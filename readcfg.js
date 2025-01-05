let fs = require('fs')
function readcfg (flag)  {
/*   const resp = fs.readFileSync('../cfg.json', 'utf8',)
  const json = JSON.parse(resp) */
  let resp = {}
  if (fs.existsSync('../config/config.js'))  resp = fs.readFileSync('../config/config.js', 'utf8',)
  if (fs.existsSync('../config.js'))  resp = fs.readFileSync('../config.js', 'utf8',)
  if (fs.existsSync('./config.js'))  resp = fs.readFileSync('./config.js', 'utf8',)
      // console.log('resp ->', resp)
  const json = eval(resp)
  if (flag)  console.log('json ->', json)
  return json
}

module.exports = {
  readcfg: readcfg,
}