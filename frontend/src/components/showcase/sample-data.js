// Dữ liệu mẫu của trang mẫu (spec 004, FR-040). Không phải số thật: trang mẫu không đọc và không ghi dữ liệu thật.
// Deterministic (no Math.random) so screenshots are stable from run to run.
export const TODAY='2026-11-10'
export const SAMPLE_NOTE='Dữ liệu mẫu'

const ZONES=[['A',13],['B',13],['C',13],['D',13],['E',12]]
const rnd=i=>{let x=(i+11)*2654435761%4294967296;x^=x>>>13;x=x*1274126177%4294967296;return (x>>>0)/4294967296}
const pickBy=(r,table)=>{let acc=0;for(const [v,w] of table){acc+=w;if(r<acc)return v}return table[table.length-1][0]}

export const lots=ZONES.flatMap(([zone,n],z)=>Array.from({length:n},(_,k)=>{
 const i=z*13+k,code=zone+(k+1),r=rnd(i)
 return {
  code,zone,
  report:pickBy(rnd(i+101),[['empty',.22],['entered',.18],['sent',.3],['confirmed',.3]]),
  care:pickBy(r,[['ok',.62],['due',.24],['overdue',.14]]),
  harvest:pickBy(rnd(i+57),[['empty',.35],['ok',.4],['due',.25]]),
  quarantine:rnd(i+313)<.09?'quarantine':'ok',
  area:Number((3.2+rnd(i+7)*1.6).toFixed(2)),trees:Math.round(7800+rnd(i+9)*2400),
 }
}))

// The weekly ribbon cycle: one colour per cutting week; two-colour ribbons after the base six.
export const ribbonBatches=[
 {code:'XANH_DUONG',week:35,cut:236,bagged:231,harvested:198,left:31,age:10},
 {code:'XANH_LA',week:36,cut:248,bagged:244,harvested:120,left:121,age:9},
 {code:'XANH_LA_DO',week:37,cut:251,bagged:247,harvested:12,left:233,age:9},
 {code:'TRANG',week:38,cut:242,bagged:240,harvested:0,left:238,age:8},
 {code:'TIM',week:39,cut:229,bagged:226,harvested:0,left:224,age:7},
 {code:'CAM',week:40,cut:255,bagged:250,harvested:0,left:252,age:6},
 {code:'DEN',week:41,cut:262,bagged:259,harvested:0,left:258,age:5},
 {code:'DO',week:43,cut:113,bagged:108,harvested:0,left:113,age:3},
 {code:'TRANG',week:44,cut:182,bagged:120,harvested:0,left:182,age:2},
 {code:'TIM',week:45,cut:236,bagged:0,harvested:0,left:236,age:1},
]

// Weekly forecast vs actual (bunches), ISO weeks 40–53/2026. Past weeks have an actual; the band is the forecast range.
const FORECAST=[5820,6110,6390,6050,6480,6900,7120,7350,7010,6720,6450,6880,7240,7600]
const ACTUAL=[5610,6240,6180,5890,6520,6640]
export const forecastWeeks=FORECAST.map((forecast,i)=>({year:2026,week:40+i,forecast,low:Math.round(forecast*.92),high:Math.round(forecast*1.07),actual:ACTUAL[i]??null}))

// Bunches still on the plants by age (weeks since cutting); 9–11 weeks is the harvest window in this sample.
export const ageBins=[
 {age:1,count:236,ribbon:'TIM'},{age:2,count:182,ribbon:'TRANG'},{age:3,count:113,ribbon:'DO'},{age:4,count:0},
 {age:5,count:258,ribbon:'DEN'},{age:6,count:252,ribbon:'CAM'},{age:7,count:224,ribbon:'TIM'},{age:8,count:238,ribbon:'TRANG'},
 {age:9,count:354,ripe:true,ribbon:'XANH_LA'},{age:10,count:31,ripe:true,ribbon:'XANH_DUONG'},{age:11,count:0,ripe:true},{age:12,count:0},
]

export const todayLots=[
 {code:'A5',zone:'A',state:'entered',line:'Cắt bắp 12 buồng · Chích bắp 8 buồng',ribbons:[{code:'CAM',week:40,count:12},{code:'TIM',week:45,count:17},{code:'TRANG',week:44,count:6},{code:'DO',week:43,count:13}],facts:['3,96 ha','9.328 cây']},
 {code:'A7',zone:'A',state:'sent',line:'Bao buồng 34 buồng',ribbons:[{code:'XANH_LA',week:36,count:41},{code:'DEN',week:41,count:22}],facts:['4,12 ha','9.710 cây']},
 {code:'B2',zone:'B',state:'confirmed',line:'Thu hoạch 58 buồng · 1.640 kg',ribbons:[{code:'XANH_DUONG',week:35,count:9},{code:'XANH_LA_DO',week:37,count:27}],facts:['3,71 ha']},
 {code:'B9',zone:'B',state:'empty',todo:'Chưa nhập hôm nay: bấm để nhập',ribbons:[{code:'TIM',week:39,count:31},{code:'CAM',week:40,count:18}],quarantineUntil:'2026-11-14',facts:['Được giao: Phun phòng nấm']},
 {code:'C4',zone:'C',state:'overdue',line:'Cắt lá: quá hạn 3 ngày',ribbons:[{code:'TRANG',week:38,count:44}],facts:['4,40 ha']},
 {code:'D11',zone:'D',state:'due',line:'Làm cỏ: đến hạn hôm nay',ribbons:[{code:'DEN',week:41,count:19},{code:'DO',week:43,count:7}],facts:['3,28 ha']},
]

export const careRounds=[
 {work:'Cắt lá',lot:'C4',due:'2026-11-07',cycle:21},
 {work:'Làm cỏ',lot:'D11',due:'2026-11-10',cycle:28},
 {work:'Bón phân',lot:'A2',due:'2026-11-12',cycle:30},
 {work:'Tỉa chồi',lot:'E3',due:'2026-11-21',cycle:30},
]

export const lotEvents=[
 {title:'Cắt bắp, buộc dây Cam',time:'06/10/2026',text:'Tổ 01 · 255 buồng · tuần 40',tone:'primary',icon:'scissors'},
 {title:'Phun phòng nấm',time:'31/10/2026',text:'Tổ 03 · thời gian cách ly 14 ngày',tone:'danger',icon:'drop'},
 {title:'Bao buồng',time:'03/11/2026',text:'Tổ 01 · 250 buồng',tone:'info',icon:'package'},
 {title:'Đội trưởng xác nhận báo cáo ngày',time:'09/11/2026',text:'Đội trưởng · không sửa',tone:'success',icon:'check-circle'},
]

export const shifts=[
 {date:'2026-11-10',name:'Sáng',team:'Xưởng đóng gói 1',bunches:412,kg:11860,boxes:910,status:'Draft',statusLabel:'Chờ nhập kho',sources:[{lot:'B2',ribbon:'XANH_DUONG',count:58},{lot:'A7',ribbon:'XANH_LA',count:120},{lot:'C1',ribbon:'XANH_LA_DO',count:234}]},
 {date:'2026-11-09',name:'Chiều',team:'Xưởng đóng gói 1',bunches:388,kg:null,boxes:null,status:'Completed',sources:[{lot:'B5',ribbon:'XANH_DUONG',count:140},{lot:'B6',ribbon:'XANH_DUONG',count:248}]},
]

const SUPPLIERS=['Công ty TNHH Vật tư Nông nghiệp Phương Nam','Đại lý Phân bón Minh Phát','HTX Dịch vụ Nông nghiệp Tân Lập','Công ty CP Bảo vệ thực vật Sao Mai','Cửa hàng Vật tư Hưng Thịnh']
const ITEMS=[['Phân NPK 16-16-8','bao'],['Bao buồng chuối','cái'],['Dây buộc màu','cuộn'],['Thuốc phòng nấm','lít'],['Kali clorua','bao'],['Phân DAP','tấn']]
const PEOPLE=[['Nguyễn Văn An','Kho tổng'],['Trần Thị Hồng','Mua hàng'],['Lê Văn Bình','Đội khu A'],['Phạm Minh Thư','Kế toán']]
const STATES=['Draft','Pending','To Sign','Approved','To Receive','Completed','Rejected','Cancelled']
export const purchaseRows=Array.from({length:14},(_,i)=>{
 const [item,unit]=ITEMS[i%ITEMS.length],[person,team]=PEOPLE[i%PEOPLE.length],qty=[120,4000,35,80,60,8,250,90,30,12,400,18,75,6][i]
 const price=[385000,1200,96000,412000,520000,14200000,1150,88000,405000,15800000,980,510000,392000,13900000][i]
 return {
  name:'PO-2026-'+String(118+i).padStart(5,'0'),date:`2026-11-${String(10-(i%9)).padStart(2,'0')}`,due:`2026-11-${String(4+((i*5)%14)).padStart(2,'0')}`,
  supplier:SUPPLIERS[i%SUPPLIERS.length],item,qty,uom:unit,amount:qty*price,status:STATES[i%STATES.length],
  received:Math.round(qty*[0,0,0,.3,.6,1,0,0,.8,.5,1,0,.25,0][i]),owner:person,team,
 }
})
export const harvestRows=[
 {lot:'B2',zone:'B',ribbon:'XANH_DUONG',week:35,cut:236,harvested:198,left:31,kg:5544,crew:'Tổ 02',lead:'Phạm Văn Lộc',status:'Confirmed'},
 {lot:'B5',zone:'B',ribbon:'XANH_LA',week:36,cut:248,harvested:120,left:121,kg:3410,crew:'Tổ 02',lead:'Phạm Văn Lộc',status:'Sent'},
 {lot:'A7',zone:'A',ribbon:'XANH_LA_DO',week:37,cut:251,harvested:12,left:233,kg:338,crew:'Tổ 01',lead:'Lê Văn Bình',status:'Draft'},
 {lot:'C1',zone:'C',ribbon:'XANH_LA_DO',week:37,cut:240,harvested:0,left:240,kg:null,crew:'Tổ 04',lead:'Trần Văn Nam',status:'Quarantine'},
 {lot:'D3',zone:'D',ribbon:'TRANG',week:38,cut:242,harvested:0,left:238,kg:null,crew:'Tổ 05',lead:'Võ Thị Lan',status:'Pending'},
]
