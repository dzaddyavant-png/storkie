import os
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

messages = {r: [] for r in ["general","music","football","random"]}
dms = {}  # dm_room -> [msgs]
users = {}  # sid -> {name, avatar, pic}

HTML = """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Storkie</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui}
body{background:#0b0b14;color:#fff;height:100vh;display:flex;overflow:hidden}
#sidebar{width:260px;background:#12121f;display:flex;flex-direction:column;border-right:1px solid #222;overflow-y:auto}
#logo{padding:16px;font-size:22px;font-weight:800} #logo span{color:#ff2d78}
#me{display:flex;align-items:center;gap:10px;padding:12px;border-bottom:1px solid #222;cursor:pointer}
#me img{width:42px;height:42px;border-radius:50%;object-fit:cover;background:#ff2d78}
.sec{padding:10px 12px 4px;color:#888;font-size:11px;letter-spacing:1px}
.room,.user,.dm{padding:10px 12px;margin:2px 8px;border-radius:10px;cursor:pointer;display:flex;align-items:center;gap:9px}
.room.active,.dm.active{background:#ff2d78}
.user:hover,.dm:hover{background:#1e1e32}
.user img,.dm img{width:32px;height:32px;border-radius:50%;object-fit:cover;background:#ff2d78}
.dot{width:9px;height:9px;border-radius:50%;background:#4ade80;margin-left:auto}
#main{flex:1;display:flex;flex-direction:column;min-width:0}
#top{padding:12px 16px;background:#12121f;border-bottom:1px solid #222;display:flex;justify-content:space-between}
#chat{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:78%;padding:10px 12px;border-radius:16px;background:#1e1e32;align-self:flex-start;word-break:break-word}
.msg.me{background:#ff2d78;align-self:flex-end}
.msg img.av{width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:6px}
.msg small{opacity:.7;font-size:12px}
.msg audio{width:220px;margin-top:6px}
#inputBar{display:flex;gap:8px;padding:12px;background:#12121f;align-items:center}
#m{flex:1;padding:12px 14px;border-radius:25px;border:none;background:#1e1e32;color:#fff;outline:none}
button{border:none;border-radius:25px;padding:10px 16px;background:#ff2d78;color:#fff;font-weight:700;cursor:pointer}
.iconBtn{background:#1e1e32;font-size:18px;padding:10px 12px}
.iconBtn.rec{background:red;animation:blink 1s infinite}
@keyframes blink{50%{opacity:.5}}
#modal{position:fixed;inset:0;background:rgba(0,0,0,.7);display:none;align-items:center;justify-content:center;z-index:99}
#mbox{background:#1a1a2e;padding:22px;border-radius:18px;text-align:center;width:300px}
#mbox img{width:90px;height:90px;border-radius:50%;object-fit:cover;background:#ff2d78}
@media(max-width:700px){#sidebar{width:76px} .hide{display:none}}
</style></head>
<body>
<div id=sidebar>
<div id=logo>🐦 Storkie<span>.</span></div>
<div id=me onclick="editProfile()"><img id=myAv><div class=hide><b id=myName>...</b><br><small>● Online</small></div></div>
<div class='sec hide'>ROOMS</div>
<div class=room active onclick="setRoom('general',this)"># general</div>
<div class=room onclick="setRoom('music',this)">🎵 music</div>
<div class=room onclick="setRoom('football',this)">⚽ football</div>
<div class=room onclick="setRoom('random',this)">🎲 random</div>
<div class='sec hide'>DIRECT MESSAGES</div>
<div id=dmList><div style='padding:0 12px;color:#666;font-size:13px'>Click an online person to DM</div></div>
<div class='sec hide'>ONLINE — <span id=onlineCount>0</span></div>
<div id=onlineList></div>
</div>
<div id=main>
<div id=top><div><b id=roomTitle># general</b><br><small id=typing></small></div><small>Storkie • Fast</small></div>
<div id=chat></div>
<div id=inputBar>
<label style='cursor:pointer'>📷<input type=file id=picInput accept='image/*' hidden></label>
<button class=iconBtn id=micBtn onclick='toggleVoice()'>🎤</button>
<input id=m placeholder='Type a message...'><button onclick='send()'>Send ➤</button>
</div>
</div>
<div id=modal onclick="if(event.target==this)this.style.display='none'"><div id=mbox><img id=pImg><h3 id=pName style='margin:10px 0 4px'></h3><p style='color:#4ade80'>● Online</p><p style='color:#aaa;margin:8px 0'>Storkie user 🐦</p><input id=editName placeholder='Your name' style='width:100%;padding:10px;border-radius:10px;border:none;background:#222;color:#fff;margin:5px 0'><br><button onclick='saveProfile()'>Save Profile</button> <button onclick='openDMFromProfile()' style='background:#1e1e32'>💬 Message</button><br><button onclick="document.getElementById('modal').style.display='none'" style='background:#333;margin-top:8px'>Close</button></div></div>
<script src='https://cdn.socket.io/4.7.2/socket.io.min.js'></script>
<script>
let socket=io();
let name=localStorage.getItem('storkie_name')||prompt('Your name?')||'Guest';
localStorage.setItem('storkie_name',name);
let myPic=localStorage.getItem('storkie_pic')||'';
let currentRoom='general'; let currentDM=null; let profileUser=null;
let mediaRec=null, chunks=[], isRec=false;
function avUrl(pic,n){return pic||('https://ui-avatars.com/api/?name='+encodeURIComponent(n||'?')+'&background=ff2d78&color=fff&bold=true');}
document.getElementById('myName').innerText=name;
document.getElementById('myAv').src=avUrl(myPic,name);
function setRoom(r,el){currentRoom=r;currentDM=null;document.querySelectorAll('.room,.dm').forEach(x=>x.classList.remove('active'));if(el)el.classList.add('active');document.getElementById('roomTitle').innerText='# '+r;document.getElementById('chat').innerHTML='';socket.emit('join',{name:name,pic:myPic,room:r});}
function openDM(other){if(other==name)return;let key=['dm',...[name,other].sort()].join('_');currentRoom=key;currentDM=other;document.querySelectorAll('.room,.dm').forEach(x=>x.classList.remove('active'));document.getElementById('roomTitle').innerText='💬 '+other;document.getElementById('chat').innerHTML='';socket.emit('join_dm',{name:name,pic:myPic,room:key,other:other});let list=document.getElementById('dmList');if(!document.getElementById('dm-'+other)){let d=document.createElement('div');d.className='dm active';d.id='dm-'+other;d.innerHTML=`<img src='${avUrl('',other)}'> <span class=hide>${other}</span>`;d.onclick=()=>openDM(other);list.appendChild(d);}}
function openDMFromProfile(){if(profileUser)openDM(profileUser);document.getElementById('modal').style.display='none';}
function addMsg(d){let c=document.getElementById('chat');let div=document.createElement('div');div.className='msg'+(d.name==name?' me':'');let body=d.type=='voice'?`<audio controls src='${d.audio}'></audio><div>🎤 Voice note</div>`:`<div>${d.text||''}</div>`;div.innerHTML=`<img class=av src='${avUrl(d.pic,d.name)}'> <b>${d.name}</b> <small>${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</small>${body}`;c.appendChild(div);c.scrollTop=c.scrollHeight;}
function send(){let inp=document.getElementById('m');if(!inp.value.trim())return;let data={name:name,pic:myPic,text:inp.value,room:currentRoom,id:Date.now()};addMsg(data);socket.emit('message',data);inp.value='';}
document.getElementById('m').addEventListener('keydown',e=>{if(e.key=='Enter')send();socket.emit('typing',{name:name,room:currentRoom,typing:true});});
document.getElementById('picInput').addEventListener('change',e=>{let f=e.target.files[0];if(!f)return;let r=new FileReader();r.onload=()=>{myPic=r.result;localStorage.setItem('storkie_pic',myPic);document.getElementById('myAv').src=myPic;socket.emit('join',{name:name,pic:myPic,room:currentRoom});};r.readAsDataURL(f);});
function editProfile(){profileUser=null;document.getElementById('pImg').src=avUrl(myPic,name);document.getElementById('pName').innerText=name;document.getElementById('editName').value=name;document.getElementById('modal').style.display='flex';}
function saveProfile(){let n=document.getElementById('editName').value.trim();if(n){name=n;localStorage.setItem('storkie_name',n);document.getElementById('myName').innerText=n;document.getElementById('myAv').src=avUrl(myPic,n);socket.emit('join',{name:name,pic:myPic,room:currentRoom});}document.getElementById('modal').style.display='none';}
function showUser(n,p){profileUser=n;document.getElementById('pImg').src=avUrl(p,n);document.getElementById('pName').innerText=n;document.getElementById('editName').value='';document.getElementById('modal').style.display='flex';}
async function toggleVoice(){if(!isRec){try{let s=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];mediaRec=new MediaRecorder(s);mediaRec.ondataavailable=e=>chunks.push(e.data);mediaRec.onstop=()=>{let b=new Blob(chunks,{type:'audio/webm'});let r=new FileReader();r.onload=()=>{let data={name:name,pic:myPic,room:currentRoom,type:'voice',audio:r.result,id:Date.now()};addMsg(data);socket.emit('message',data);};r.readAsDataURL(b);};mediaRec.start();isRec=true;document.getElementById('micBtn').classList.add('rec');document.getElementById('micBtn').innerText='⏹️';}catch(e){alert('Allow mic to send voice notes');}}else{mediaRec.stop();isRec=false;document.getElementById('micBtn').classList.remove('rec');document.getElementById('micBtn').innerText='🎤';}}
socket.on('connect',()=>{socket.emit('join',{name:name,pic:myPic,room:currentRoom});});
socket.on('history',msgs=>msgs.forEach(addMsg));
socket.on('message',addMsg);
socket.on('online',list=>{document.getElementById('onlineCount').innerText=list.length;document.getElementById('onlineList').innerHTML=list.map(u=>`<div class=user onclick="showUser('${u.name}','${u.pic||''}')"><img src='${avUrl(u.pic,u.name)}'><span class=hide>${u.name}</span><span class=dot></span></div>`).join('');});
socket.on('typing',d=>{document.getElementById('typing').innerText=d.typing?d.name+' is typing...':'';setTimeout(()=>document.getElementById('typing').innerText='',2000);});
</script></body></html>
"""

@app.route("/")
def index(): return HTML

def send_online():
    seen={}
    for u in users.values(): seen[u["name"]]=u
    socketio.emit("online", list(seen.values()))

@socketio.on("join")
def on_join(d):
    users[request.sid]={"name":d.get("name"),"pic":d.get("pic","")}
    join_room(d.get("room","general"))
    emit("history", messages.get(d.get("room","general"), []))
    send_online()

@socketio.on("join_dm")
def on_join_dm(d):
    users[request.sid]={"name":d.get("name"),"pic":d.get("pic","")}
    room=d.get("room")
    join_room(room)
    emit("history", dms.get(room, []))
    send_online()

@socketio.on("message")
def on_msg(d):
    room=d.get("room","general")
    if room.startswith("dm_"):
        dms.setdefault(room, []).append(d)
        if len(dms[room])>100: dms[room]=dms[room][-100:]
    else:
        messages.setdefault(room, []).append(d)
        if len(messages[room])>100: messages[room]=messages[room][-100:]
    emit("message", d, room=room, include_self=False)

@socketio.on("typing")
def on_typing(d):
    emit("typing", d, room=d.get("room","general"), include_self=False)

@socketio.on("disconnect")
def on_disc():
    users.pop(request.sid, None)
    send_online()

if __name__=="__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
