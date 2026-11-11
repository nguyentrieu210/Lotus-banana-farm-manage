// The showcase lists the whole kit (spec 004, FR-039 to FR-041, SC-003), says its numbers are sample data, and stays
// out of the production build.
import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,readdirSync,existsSync} from 'node:fs'

const src=new URL('../src/',import.meta.url)
const read=p=>readFileSync(new URL(p,src),'utf8')
const showcase=[read('components/UiShowcase.vue'),...readdirSync(new URL('components/showcase/',src)).filter(f=>f.endsWith('.vue')).map(f=>read('components/showcase/'+f))].join('\n')
const used=name=>new RegExp('<'+name+'[\\s/>]').test(showcase)

test('every agritech component appears on the showcase',()=>{
 const agri=readdirSync(new URL('components/agri/',src)).filter(f=>f.endsWith('.vue')).map(f=>f.replace('.vue',''))
 assert.ok(agri.length>=15)
 const exported=read('components/agri/index.js')
 // RibbonDot is drawn inside the chips, the legend and the strip, and on its own in Nền.
 for(const name of agri){assert.match(exported,new RegExp(`as ${name}\\}`),name+' is exported');assert.ok(used(name),name+' is on the showcase')}
})

test('every desktop primitive of the kit appears on the showcase',()=>{
 const NAMES={'status-chip':'StatusChip',banner:'Banner','stat-tile':'StatTile',progress:'Progress',switch:'Switch',segmented:'Segmented','number-stepper':'NumberStepper',avatar:'Avatar',steps:'Steps',timeline:'Timeline','description-list':'DescriptionList',button:'UiButton',input:'UiInput',select:'UiSelect',textarea:'UiTextarea',checkbox:'Checkbox','form-field':'FormField',combobox:'Combobox','date-picker':'DatePicker','dropdown-menu':'DropdownMenu',tooltip:'Tooltip',popover:'Popover',sheet:'Sheet',pagination:'Pagination',skeleton:'UiSkeleton'}
 for(const [folder,tag] of Object.entries(NAMES)){assert.ok(existsSync(new URL(`components/ui/${folder}/index.js`,src)),folder);assert.ok(used(tag),tag+' is on the showcase')}
 assert.ok(used('ProgressRing'))
 assert.match(showcase,/toast\.success\(/,'toasts can be triggered')
})

test('the phone kit, the shared table and the screen patterns are shown',()=>{
 for(const tag of ['LotusMobileNetBar','DataTable','ListPage','WorkspaceModal','WorkspaceTabs','DesktopEmptyState'])assert.ok(used(tag),tag)
 for(const id of ['nen','thanh-phan','bang','dien-thoai','nong-nghiep','man-hinh'])assert.match(read('components/UiShowcase.vue'),new RegExp(`id:'${id}'`),id)
 assert.match(read('components/UiShowcase.vue'),/mode=light\|dark\|outdoor/,'a section can be opened alone in a mode, for screenshots')
})

test('sample data is labelled as such and is not real records',()=>{
 const sample=read('components/showcase/sample-data.js')
 assert.match(sample,/Dữ liệu mẫu/)
 assert.match(read('components/UiShowcase.vue'),/SAMPLE_NOTE/)
 assert.doesNotMatch(sample,/Math\.random\(/,'deterministic, so screenshots compare')
 assert.doesNotMatch(showcase,/\bapi\(|fetch\(|frappe\.|\/api\/method/,'the showcase never calls the server')
})

test('the showcase is built by its own config, never by the production build',()=>{
 assert.doesNotMatch(readFileSync(new URL('../vite.config.js',import.meta.url),'utf8'),/showcase/)
 const config=readFileSync(new URL('../vite.showcase.config.js',import.meta.url),'utf8')
 assert.match(config,/input:\['showcase\.html'\]/)
 assert.match(config,/outDir:process\.env\.LOTUS_SHOWCASE_OUT\|\|'dist-showcase'/,'it never writes into the served assets')
 assert.match(readFileSync(new URL('../../.gitignore',import.meta.url),'utf8'),/frontend\/dist-showcase\//)
})
