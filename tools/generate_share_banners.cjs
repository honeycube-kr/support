// 로컬 전용. 기존 게임 PNG로 모드/언어 텍스트 없는 공통 v2 JPG 한 장을 생성한다.
// node tools/generate_share_banners.cjs GAME_CHECKOUT RUNTIME_NODE_MODULES
// 이미 생성된 파일은 불변이며 덮어쓰지 않는다.
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const root = path.resolve(__dirname, '..');
const [game, modules] = process.argv.slice(2);
if (!game || !modules) throw Error('GAME_CHECKOUT and RUNTIME_NODE_MODULES required');
const runtime = createRequire(path.join(path.resolve(modules), '__share.cjs'));
const {chromium} = runtime('playwright');
const sharp = runtime('sharp');
const data = file => 'data:image/png;base64,' + fs.readFileSync(path.join(game, file)).toString('base64');
const logo = data('assets/images/branding/logo.png');
const background = data('assets/images/share/block_background.png');
const file = path.join(root,'images/share/v2/common.jpg');
if(fs.existsSync(file)) throw Error('Refusing to overwrite immutable banner: '+file);
(async()=>{
 const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try {
 const page = await browser.newPage({viewport:{width:1200,height:630},deviceScaleFactor:1});
  fs.mkdirSync(path.dirname(file),{recursive:true});
  await page.setContent(`<!doctype html><html><style>*{box-sizing:border-box}html,body{margin:0;width:1200px;height:630px}body{background:linear-gradient(#10223822,#10223822),url('${background}') center/cover;display:flex;align-items:center;justify-content:center}img{display:block;width:700px;height:auto}</style><body><img src="${logo}" alt="Brick Square"></body></html>`);
  await page.locator('img').evaluate(img=>img.decode());
  const png = await page.screenshot({type:'png'});
  await sharp(png).jpeg({quality:88,mozjpeg:true}).toFile(file);
  const meta=await sharp(file).metadata();
  if(meta.format!=='jpeg'||meta.width!==1200||meta.height!==630||fs.statSync(file).size>200000)throw Error('Banner validation failed');
  console.log(path.relative(root,file),fs.statSync(file).size,meta.width,meta.height,meta.format);
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
