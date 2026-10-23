// 로컬 전용. 기존 게임의 실제 PNG를 사용해 v1 JPG를 한 번 생성한다.
// node tools/generate_share_banners.cjs GAME_CHECKOUT RUNTIME_NODE_MODULES
// v1은 불변이다. 재생성은 빈 출력 경로 또는 새 버전에만 수행한다.
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
const labels = {ko:['스테이지','데일리 퍼즐','서바이벌'],en:['Stage','Daily Puzzle','Survival'],ja:['ステージ','デイリーパズル','サバイバル']};
const modes = ['stage','daily','survival'];
const colors = ['#6bb7ff','#77d9ac','#ffd86b'];
(async()=>{
 const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try {
 const page = await browser.newPage({viewport:{width:1200,height:630},deviceScaleFactor:1});
 for(const [lang,names] of Object.entries(labels)) for(let i=0;i<3;i++) {
  const file = path.join(root,'images/share/v1',lang,modes[i]+'.jpg');
  if(fs.existsSync(file)) throw Error('Refusing to overwrite immutable banner: '+file);
  fs.mkdirSync(path.dirname(file),{recursive:true});
  await page.setContent(`<!doctype html><html lang="${lang}"><style>*{box-sizing:border-box}html,body{margin:0;width:1200px;height:630px}body{background:#102238 url('${background}') center/cover;display:flex;align-items:center;justify-content:center}main{text-align:center;width:1000px}img{display:block;width:760px;height:280px;object-fit:contain;margin:0 auto 44px}h1{color:#fff;font:700 48px/1.2 'Malgun Gothic','Yu Gothic',sans-serif;margin:0}i{display:block;width:160px;height:4px;background:${colors[i]};margin:28px auto 0}</style><main><img src="${logo}" alt="Brick Square"><h1>${names[i]}</h1><i></i></main>`);
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('img').evaluate(img=>img.decode());
  const png = await page.screenshot({type:'png'});
  await sharp(png).jpeg({quality:88,mozjpeg:true}).toFile(file);
  const meta=await sharp(file).metadata();
  if(meta.format!=='jpeg'||meta.width!==1200||meta.height!==630||fs.statSync(file).size>200000)throw Error('Banner validation failed');
  console.log(path.relative(root,file),fs.statSync(file).size,meta.width,meta.height,meta.format);
 }
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
