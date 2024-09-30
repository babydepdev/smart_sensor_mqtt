const  mqtt = require('mqtt');

const {
  readcfg,
} = require('./readcfg')
const cfg = readcfg();
// console.log(cfg)

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const packageDefinition = protoLoader.loadSync(
  "proto/db.proto",
  {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true
  }
);
const dbaseproject = grpc.loadPackageDefinition(packageDefinition).dbaseproject;
const dbase = new dbaseproject.DbaseProject(
  cfg.dbaseIP+':'+cfg.dbasePort, 
  grpc.credentials.createInsecure(), 
  {'grpc.max_send_message_length': 50*1024*1024, 'grpc.max_receive_message_length': 50*1024*1024}
);

const packageDefinition2 = protoLoader.loadSync(
  "proto/gateway.proto",
  {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true
  }
);
const gatewayproject = grpc.loadPackageDefinition(packageDefinition2).gatewayproject;
const gateway = new gatewayproject.GatewayProject(
  cfg.gatewayIP+':'+cfg.gatewayPort, 
  grpc.credentials.createInsecure(), 
  {'grpc.max_send_message_length': 50*1024*1024, 'grpc.max_receive_message_length': 50*1024*1024}
);

const redis = require('redis');
const client = redis.createClient({ socket: { host: cfg.redisIP,  port: cfg.redisPort, }});

let redisConnect = false
client.on('connect', function() {
  redisConnect = true
  console.log('\x1b[32m%s\x1b[0m', 'Redis connected ->', redisConnect);  //green
});

client.on('reconnecting', function() {
  console.log('\x1b[33m%s\x1b[0m', 'Redis reconnecting ->', redisConnect);  //green
});

client.on('error', function() {
  redisConnect = false
  console.log('\x1b[31m%s\x1b[0m', 'Redis error ->', redisConnect);  //green
});

let localSiteID = null;
let siteOnline = [];
let siteTimeout = [];
let devices = []
// let writeBuffer = [];

function _dbIsReady(req) {
  return new Promise(resolve => {
    dbase.dbIsReady(req, (err, resp) => {
      resolve(resp)
    });
  });
}

function readAllConfig() {
  return new Promise(resolve => {
    dbase.readDocument({ 
      collection: 'Config',
      query: JSON.stringify({}),
      options: JSON.stringify({ encrypt: false })
    }, (err, resp) => {
      (async () => {
        if (resp)  {
          const sites = JSON.parse(resp.data) 
          console.log('sites.length ->', sites.length)
          resolve(sites)
        }
        else  resolve([])
      })();
    });
  });
}

function readAllGroup() {
  return new Promise(resolve => {
    dbase.readDocument({ 
      collection: 'Server',
      query: JSON.stringify({}),
    }, (err, resp) => {
      (async () => {
        if (resp)  {
          const groups = JSON.parse(resp.data) 
          console.log('groups.length ->', groups.length)
          resolve(groups)
        }
        else  resolve([])
      })();
    });
  });
}

function readAllDevice(site) {
  return new Promise(resolve => {
    dbase.readDocument({ 
      base: site.siteID,
      collection: 'Device',
      query: JSON.stringify({}),
    }, (err, resp) => {
      (async () => {
        if (resp)  {
          const devices = JSON.parse(resp.data) 
          console.log('devices.length ->', site.siteID, devices.length)
          resolve(devices)
        }
        else  resolve([])
      })();
    });
  });
}

function sleep(delay = 0) {
  return new Promise(resolve => {
    setTimeout(resolve, delay);
  });
}

function checkActivate(write) {
  return new Promise(resolve => {
    gateway.checkActivateV2({ write: write, }, (err, resp) => {
      // console.log('checkActivateV2 ->', err, resp)
      let status = false
      if (resp)  status = resp.status
      resolve(status)
    })
  });
}

function deviceInit() {
  return new Promise(resolve => {
    (async () => {

      siteTimeout = []
      if (cfg.server)  {
        const groups = await readAllGroup()
        for (let i in groups)  siteTimeout.push({ id: groups[i].serverID, timeout: groups[i].timeout })

        const sites = await readAllConfig()
        if (sites.length)  localSiteID = sites[0].siteID
        for (let i in sites)  {
          // console.log(sites[i])
          if (sites[i].activate == 'Demo')  siteTimeout.push({ id: sites[i].siteID, timeout: sites[i].timeout })
        }
      }
      else  {
        const sites = await readAllConfig()
        if (sites.length)  localSiteID = sites[0].siteID
        for (let i in sites)  siteTimeout.push({ id: sites[i].siteID, timeout: sites[i].timeout })
      }
     
      devices = []
      for (let i in siteTimeout)  {
        const temp = await readAllDevice({ siteID: siteTimeout[i].id })
        for (let j in temp)  {
          if (temp[j].connection == 'MQTT')  devices.push(temp[j])
        }
      }
      console.log('MQTT devices length ->', devices.length) 

      resolve()

    })();
  });
}

async function mqttInit(mqInfo)  {

  console.log('mqttInit ->', mqInfo);

  await deviceInit()

  let server  = mqtt.connect(mqInfo.host, { username: mqInfo.username, password: mqInfo.password });
  server.on('connect', function () {
    server.subscribe(mqInfo.subscribe, function (err) {
      console.log('MQTT initialization done!', err);
    })
  })       

  server.on('message', function (topic, message) {
    // (async () => {
    let data = null
    try {
      data = JSON.parse(message.toString()); 
    }
    catch(e)  {
      console.log('JSON.parse error...');
      return;
    }

    if (!data) {
        console.log('MQTT -> No data!')
      return;
    }

    if (!data.siteID)  {
      console.log('MQTT -> No siteID!')
      return;
    }

    if (!cfg.server)  {
      if (data.siteID != localSiteID)  {
        console.log('MQTT -> No siteID!')
        return;
      }
    }

    if (!data.deviceID || !data.date || !data.offset || !data.connection || !data.tagObj)  {
      console.log('MQTT ->', data.siteID, '-> Data format error!');      
      return
    }

    if (!data.tagObj.length)  {
      console.log('MQTT ->', data.siteID, '-> Data format error!');      
      return
    }

    if (data.connection != 'MQTT')  {
      console.log('MQTT ->', data.siteID, '-> Connecttion is not MQTT!');
      return
    }

    let state = false
    const device = devices.find( e => (e.siteID == data.siteID && e.deviceID == data.deviceID))
    if (device)  {
      let count = 0
      if (device.tags.length == data.tagObj.length)  {
        for (let j in device.tags)  {
          if (device.tags[j].label == data.tagObj[j].label)  {
            // console.log(data.tagObj[j], device.tags[j], )
            data.tagObj[j].sync = device.tags[j].sync
            data.tagObj[j].show = device.tags[j].show
            data.tagObj[j].record = device.tags[j].record
            data.tagObj[j].update = device.tags[j].update
            count++
          }
        }  
      }
      if (count == device.tags.length)  state = true
    }

    if (!state)  {
      console.log('MQTT ->', data.siteID, '-> Data format error!');
      return  
    }

    /* console.log(data) */
    let online = false;
    const site = siteOnline.find( e => e.siteID == data.siteID)
    if (site)  {
      let flag = false;
      for (let j in site.devices)  {
        if (site.devices[j].deviceID == data.deviceID)  {
          flag = true;
          site.devices[j] = data;              
          break;
        }
      }
      if (!flag)  site.devices.push(data);
      site.timeout = 0;
      online = true;
    }

    if (!online)  {
      siteOnline.push({
        siteID: data.siteID,
        devices: [data],
        timeout: 0,
      })
      console.log(data.siteID, 'MQTT new connection!'); 
    }
    // })();
  })  

  server.on('error', function () {
    console.log('mqtt error...');
    process.exit(1);
  })

  server.on('disconnect', function () {
    console.log('mqtt disconnect...');
    process.exit(1);
  })

  server.on('close', function () {
    console.log('mqtt close...');
    process.exit(1);
  })

  server.on('offline', function () {
    console.log('mqtt offline...');
    process.exit(1);
  })
  
  server.on('end', function () {
    console.log('mqtt end...');
    process.exit(1);
  })

  async function repeat()  {

    for (let i in siteTimeout)  {
      const site = siteOnline.find( e => e.siteID == siteTimeout[i].id)
      if (site)  {
        if (++site.timeout > siteTimeout[i].timeout)  {
          console.log(site.siteID, 'MQTT connection close!')
          siteOnline = siteOnline.filter( e => e.siteID != site.siteID)
        }  
      }
    }    
    // console.log(siteOnline);

    let activate = await checkActivate(false);
    // console.log('Activate ->', activate);  
    for (let i in siteOnline)  {      
      if (!cfg.server && !activate)  continue;
      let site = siteOnline[i];
      let call = gateway.realtimeUpdate((err, resp) => {
        // console.log(err, resp);
      });
      for (let j in site.devices)  {
        call.write(site.devices[j]);
        await sleep(1);
      }
      call.end();                  
      await sleep(1);
    }
     
    let KEY = 'RESTART_MQTT'
    if (!cfg.server)  KEY = localSiteID+'_RESTART_MQTT'
    const str = await client.get(KEY)
    // console.log('*** ->', KEY, str)
    if (str == 'MQTT')  {
      console.log('RESTART MQTT ->', KEY)
      await client.del(KEY)
      for (let i in siteOnline)  {
        await client.del(siteOnline[i].siteID+'_MQTT')
      }
      await deviceInit()
    } 

    await sleep(1e3);
    repeat();
  }

  repeat();

  function getWrite(siteID)  {
    return new Promise(resolve => {
      gateway.getWriteBuffer( { siteID: siteID, connection: 'MQTT' }, (err, resp) => {
        // console.log(err, resp);
        if (resp)  {
          if (resp.siteID != '')  {
            // console.log(err, resp);
            // writeBuffer.push(resp);
            server.publish(mqInfo.publish, JSON.stringify(resp), () =>{
              // console.log(e);
              resolve(resp);
            })
          }
          else  resolve(null);
        }
        else  resolve(null);
      }); 
    });  
  }

  async function getWriteBuffer() {
    for (var i in siteOnline)  {
      let resp = await getWrite(siteOnline[i].siteID);
      if (resp)  {
        console.log(resp);  
      }
    }
    await sleep(1e3);
    getWriteBuffer();
  }
  getWriteBuffer();     

}

async function main ()  {
  
  const resp = await _dbIsReady({})
  if (resp && resp.status)  {
    console.log('DB service is ready ->', resp);
  }
  else  {
    console.log('DB service is not ready ->', resp);
    await sleep(1e3*10)
    main()
    return
  }  

  let mqInfo = { 
    host: 'http://www.somha-iot.com', 
    username: 'ajbear', 
    password: 'ajbear1969', 
    subscribe: 'ajbear/bar',
    publish: 'ajbear/bar',
  }
  if (cfg.mqInfo)  mqInfo = cfg.mqInfo

  if (cfg.server)  {
    mqttInit(mqInfo);
  }
  else  {
    async function client()  {
      const sites = await readAllConfig();
      // console.log(sites);
      if (sites && sites.length)  {
        localSiteID = sites[0].siteID
        mqttInit(mqInfo);
      }
      else  {
        await sleep(1e3*10);
        client();
        return;
      }
    }
    client();
  }
}

if (require.main === module) {
  (async () => {
    console.log('Waiting redis ->', redisConnect)
    await client.connect()
    main();
  })();         
}
