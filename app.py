import os
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Memory storage
messages = {r: [] for r in ["general","music","football","random"]}
users = {}  # sid -> {name, avatar, pic}

HTML = """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Storkie</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui}
body{background:#0b0b14;color:#fff;height:100vh;display:flex;overflow:hidden}
#sidebar{width:250px;background:#12121f;display:flex;flex-direction:column;border-right:1px solid #222}
#logo{padding:16px;font-size:22px;font-weight:800} #logo span{color:#ff2d78}
#me{display:flex;align-items:center;gap:10px;padding:12px;border-bottom:1px solid #222;cursor:pointer}
#me img{width:42px;height:42px;border-radius:50%;object-fit:cover;background:#333}
#me b{font-size:15px} #me small{color:#4ade80;font-size:12px}
.sec{padding:10px 12px 4px;color:#888;font-size:11px;letter-spacing:1px}
.room{padding:10px 12px;margin:2px 8px;border-radius:10px;cursor:pointer}
.room.active{background:#ff2d78}
.user{display:flex;align-items:center;gap:9px;padding:8px 12px;margin:1px 8px;border-radius:10px;cursor:pointer}
.user:hover{background:#1e1e32}
.user img{width:32px;height:32px;border-radius:50%;object-fit:cover;background:#333}
.dot{width:9px;height:9px;border-radius:50%;background:#4ade80;margin-left:auto}
#main{flex:1;display:flex;flex-direction:column;min-width:0}
#top{padding:12px 16px;background:#12121f;border-bottom:1px solid #222;display:flex;justify-content:space-between;align-items:center}
#top b{font-size:18px} #top small{color:#aaa}
#chat{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:75%;padding:10px 12px;border-radius:16px;background:#1e1e32;align-self:flex-start}
.msg.me{background:#ff2d78;align-self:flex-end}
.msg img.av{width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:6px}
.msg small{opacity:.7;font-size:12px}
#inputBar{display:flex;gap:8px;padding:12px;background:#12121f}
#m{flex:1;padding:12px 14px;border-radius:25px;border:none;background:#1e1e32;color:#fff;outline:none}
button{border:none;border-radius:25px;padding:10px 16px;background:#ff2d78;color:#fff;font-weight:700;cursor:pointer}
#profileModal{position:fixed;inset:0;background:rgba(0,0,0,.7);display:none;align-items:center;justify-content:center;z-index:99}
#profileBox{background:#1a1a2e;padding:22px;border-radius:18px;text-align:center;width:300px}
#profileBox img{width:90px;height:90px;border-radius:50%;object-fit:cover}
@media(max-width:700px){#sidebar{width:78px} #sidebar .hide{display:none} .room,.user{justify-content:center}}
</style></head>
<body>
<div id=sidebar>
<div id=logo>🐦 Storkie<span>.</span></div>
<div id=me onclick="editProfile()"><img id=myAv src=''><div class=hide><b id=myName>...</b><br><small>● Online</small></div></div>
<div class='sec hide'>ROOMS</div>
<div class=room active onclick="setRoom('general',this)"># general</div>
<div class=room onclick="setRoom('music',this)">🎵 music</div>
<div class=room onclick="setRoom('football',this)">⚽ football</div>
<div class=room onclick="setRoom('random',this)">🎲 random</div>
<div class='sec hide'>ONLINE — <span id=onlineCount>0</span></div>
<div id=onlineList></div>
</div>
<div id=main>
<div id=top><div><b id=roomTitle># general</b><br><small id=typing></small></div><small>Storkie • Fast</small></div>
<div id=chat></div>
<div id=inputBar><label style='cursor:pointer;padding:10px'>📷<input type=file id=picInput accept='image/*' hidden></label><input id=m placeholder='Type a message...' autocomplete=off><button onclick='send()'>Send ➤</button></div>
</div>
<div id=profileModal onclick="if(event.target==this)this.style.display='none'"><div id=profileBox><img id=pImg><h3 id=pName style='margin:10px 0 4px'></h3><p id=pStatus style='color:#4ade80'>● Online</p><p id=pBio style='color:#aaa;margin:10px 0'>Storkie user 🐦</p><input id=editName placeholder='Your name' style='width:100%;padding:10px;border-radius:10px;border:none;background:#222;color:#fff;margin:5px 0'><br><button onclick='saveProfile()'>Save Profile</button><br><button onclick="document.getElementById('profileModal').style.display='none'" style='background:#333;margin-top:8px'>Close</button></div></div>
<script src='https://cdn.socket.io/4.7.2/socket.io.min.js'></script>
<script>
let socket=io();
let name=localStorage.getItem('storkie_name')||prompt('Your name?')||'Guest';
localStorage.setItem('storkie_name',name);
let myAvatar=localStorage.getItem('storkie_avatar')||'🐦';
let myPic=localStorage.getItem('storkie_pic')||'';
let currentRoom='general';
document.getElementById('myName').innerText=name;
document.getElementById('myAv').src=myPic||'https://i.imgur.com/6YQ9Z9a.png';
function setRoom(r,el){currentRoom=r;document.querySelectorAll('.room').forEach(x=>x.classList.remove('active'));el.classList.add('active');document.getElementById('roomTitle').innerText='# '+r;document.getElementById('chat').innerHTML='';socket.emit('join',{name:name,avatar:myAvatar,pic:myPic,room:r});}
function addMsg(d){let c=document.getElementById('chat');let div=document.createElement('div');div.className='msg'+(d.name==name?' me':'');div.innerHTML=(d.pic?`<img class=av src='${d.pic}'>`:`<span>${d.avatar||'🐦'} </span>`)+`<b>${d.name}</b> <small>${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</small><div>${d.text}</div>`;c.appendChild(div);c.scrollTop=c.scrollHeight;}
function send(){let inp=document.getElementById('m');if(!inp.value.trim())return;let text=inp.value;let data={name:name,avatar:myAvatar,pic:myPic,text:text,room:currentRoom,id:Date.now()};addMsg(data);socket.emit('message',data);inp.value='';socket.emit('typing',{name:name,room:currentRoom,typing:false});}
document.getElementById('m').addEventListener('keydown',e=>{if(e.key=='Enter')send();socket.emit('typing',{name:name,room:currentRoom,typing:true});});
document.getElementById('picInput').addEventListener('change',e=>{let f=e.target.files[0];if(!f)return;let r=new FileReader();r.onload=()=>{myPic=r.result;localStorage.setItem('storkie_pic',myPic);document.getElementById('myAv').src=myPic;socket.emit('join',{name:name,avatar:myAvatar,pic:myPic,room:currentRoom});};r.readAsDataURL(f);});
function editProfile(){document.getElementById('pImg').src=myPic||'https://i.imgur.com/6YQ9Z9a.png';document.getElementById('pName').innerText=name;document.getElementById('editName').value=name;document.getElementById('profileModal').style.display='flex';}
function saveProfile(){let n=document.getElementById('editName').value.trim();if(n){name=n;localStorage.setItem('storkie_name',n);document.getElementById('myName').innerText=n;socket.emit('join',{name:name,avatar:myAvatar,pic:myPic,room:currentRoom});}document.getElementById('profileModal').style.display='none';}
function showUser(u){document.getElementById('pImg').src=u.pic||'https://i.imgur.com/6YQ9Z9a.png';document.getElementById('pName').innerText=u.name;document.getElementById('profileModal').style.display='flex';}
socket.on('connect',()=>{socket.emit('join',{name:name,avatar:myAvatar,pic:myPic,room:currentRoom});});
socket.on('history',msgs=>{msgs.forEach(addMsg);});
socket.on('message',addMsg);
socket.on('online',list=>{document.getElementById('onlineCount').innerText=list.length;document.getElementById('onlineList').innerHTML=list.map(u=>`<div class=user onclick='showUser(${JSON.stringify(u).replace(/'/g,"")})'><img src='${u.pic||"https://i.imgur.com/6YQ9Z9a.png"}'><span class=hide>${u.name}</span><span class=dot></span></div>`).join('');});
socket.on('typing',d=>{document.getElementById('typing').innerText=d.typing?d.name+' is typing...':'';setTimeout(()=>document.getElementById('typing').innerText='',2000);});
</script></body></html>
"""

@app.route("/")
def index(): return HTML

@socketio.on("join")
def on_join(d):
    users[request.sid] = {"name": d.get("name"), "avatar": d.get("avatar","🐦"), "pic": d.get("pic","")}
    join_room(d.get("room","general"))
    emit("history", messages.get(d.get("room","general"), []))
    send_online()

@socketio.on("message")
def on_msg(d):
    room = d.get("room","general")
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

def send_online():
    seen={}
    for u in users.values(): seen[u["name"]]=u
    emit("online", list(seen.values()), broadcast=True)

if __name__=="__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
