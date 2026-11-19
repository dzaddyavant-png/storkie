from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import json, os, time, uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- STORAGE ---
FILE = "messages.json"
ROOMS = ["general", "music", "football", "random"]
# messages = {room: [msg, ...]}
if os.path.exists(FILE):
    try:
        with open(FILE) as f: messages = json.load(f)
    except: messages = {r: [] for r in ROOMS}
else:
    messages = {r: [] for r in ROOMS}
for r in ROOMS:
    if r not in messages: messages[r] = []

online = {}  # sid -> {name, room, avatar, pic}
typing_users = {} # room -> set names

def save():
    try:
        with open(FILE, "w") as f: json.dump(messages, f)
    except: pass

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box} body{margin:0;font-family:sans-serif;background:#0f0f1a;color:white;height:100vh;display:flex;flex-direction:column}
header{padding:12px;background:#1a1a2e;text-align:center;font-weight:900;font-size:20px}
header small{display:block;font-size:12px;opacity:.7;font-weight:400}
#rooms{display:flex;gap:6px;padding:8px;background:#16162a;overflow-x:auto}
#rooms button{padding:8px 14px;border-radius:20px;border:1px solid #333;background:#222;color:white;cursor:pointer;white-space:nowrap}
#rooms button.active{background:#ff2d78;border-color:#ff2d78}
#topinfo{display:flex;justify-content:space-between;padding:6px 12px;font-size:12px;opacity:.8;background:#16162a}
#onlineList{padding:4px 12px;font-size:12px;opacity:.8;white-space:nowrap;overflow-x:auto;background:#16162a}
#chat{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:82%;background:#222;padding:8px 10px;border-radius:14px;align-self:flex-start}
.msg.me{background:#ff2d78;align-self:flex-end}
.avatar{width:32px;height:32px;border-radius:50%;background:#444;display:flex;align-items:center;justify-content:center;font-size:18px;overflow:hidden;float:left;margin-right:8px}
.avatar img{width:100%;height:100%;object-fit:cover}
.msg b{font-size:13px} .msg p{margin:4px 0 0;font-size:15px;word-break:break-word}
.chat-img{max-width:100%;border-radius:10px;margin-top:4px}
.reacts{margin-top:6px;display:flex;gap:4px}
.reacts button{background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.3);border-radius:12px;color:white;padding:3px 7px;cursor:pointer;font-size:12px}
#typing{padding:4px 12px;font-size:12px;color:#ff9ec4;min-height:18px}
#box{display:flex;gap:6px;padding:10px;background:#1a1a2e;align-items:center}
#box input{flex:1;padding:12px;border-radius:20px;border:none;outline:none;background:#222;color:white}
#box button{padding:12px 14px;border-radius:20px;border:none;background:#ff2d78;color:white;font-weight:700;cursor:pointer}
#setup{position:fixed;inset:0;background:#0f0f1a;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;z-index:99;text-align:center}
#setup input{padding:12px;border-radius:12px;border:none;width:100%;max-width:300px;margin:10px 0}
.avatars{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.avatars span{font-size:28px;cursor:pointer;padding:6px;border-radius:10px}
.avatars span.sel{background:#ff2d78}
</style></head><body>
<header>🐦 Storkie <small>Chat with your people • <span id="onlineCount">0 Online</span></small></header>
<div id="rooms"></div>
<div id="onlineList"></div>
<div id="chat"></div>
<div id="typing"></div>
<div id="box">
<label for="file" style="padding:12px 14px;border-radius:20px;cursor:pointer;background:#222">📷</label>
<input type="file" id="file" accept="image/*" hidden>
<input id="m" placeholder="Type a message...">
<button onclick="send()">Send ➤</button>
</div>
<div id="setup">
<div id="myPic" style="font-size:60px">🐦</div>
<h2 style="margin:5px">Welcome to Storkie!</h2><p>Pick a name & avatar</p>
<input id="nameInput" placeholder="Your name... e.g Dzaddy">
<div class="avatars" id="avatarList"></div>
<input type="file" id="picInput" accept="image/*" style="background:white;color:black">
<p style="font-size:12px;opacity:.8">Optional: Upload your profile pic</p>
<button onclick="join()" style="padding:12px 20px;border-radius:12px;background:#ff2d78;color:white;border:none;font-weight:800">Join Storkie ➤</button>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
let name=localStorage.getItem('storkie_name')||"";
let myAvatar=localStorage.getItem('storkie_avatar')||"🐦";
let myPic=localStorage.getItem('storkie_pic')||"";
let socket=io();
let chat=document.getElementById('chat');
let emojis=["🐦","😎","🔥","🦁","🐱","🌟","💀","🎧","⚽","🦋"];
let avDiv=document.getElementById('avatarList');
emojis.forEach(e=>{let s=document.createElement('span');s.textContent=e;if(e==myAvatar)s.classList.add('sel');s.onclick=()=>{myAvatar=e;document.querySelectorAll('.avatars span').forEach(x=>x.classList.remove('sel'));s.classList.add('sel')};avDiv.appendChild(s)});
if(myPic){document.getElementById('myPic').innerHTML='<img src="'+myPic+'" style="width:80px;height:80px;border-radius:50%;object-fit:cover">'};
document.getElementById('picInput').addEventListener('change',function(){let f=this.files[0];if(!f)return;let r=new FileReader();r.onload=()=>{myPic=r.result;document.getElementById('myPic').innerHTML='<img src="'+myPic+'" style="width:80px;height:80px;border-radius:50%;object-fit:cover">' };r.readAsDataURL(f)});
if(name){document.getElementById('setup').style.display='none'}else{document.getElementById('nameInput').value=""}

let currentRoom = localStorage.getItem('storkie_room')||"general";
let unread=0;
if(Notification.permission==="default"){Notification.requestPermission()}

function beep(){try{let c=new (window.AudioContext||window.webkitAudioContext)();let o=c.createOscillator();o.frequency.value=880;o.connect(c.destination);o.start();setTimeout(()=>o.stop(),120)}catch(e){}}
function notify(title,body){if(document.hidden){beep();if(Notification.permission==="granted"){new Notification(title,{body:body})}document.title="("+ ++unread +") Storkie";}}
document.addEventListener('visibilitychange',()=>{if(!document.hidden){unread=0;document.title="Storkie"}});

function renderRooms(){
 let div=document.getElementById('rooms');div.innerHTML="";
 ["general","music","football","random"].forEach(r=>{
  let b=document.createElement('button');b.textContent="#"+r;if(r==currentRoom)b.classList.add('active');
  b.onclick=()=>switchRoom(r);div.appendChild(b);
 });
}
function switchRoom(r){
 currentRoom=r;localStorage.setItem('storkie_room',r);
 chat.innerHTML="";renderRooms();
 socket.emit('switch_room',{name:name,avatar:myAvatar,pic:myPic,room:r});
}
function join(){
 let n=document.getElementById('nameInput').value.trim();
 if(!n){alert("Enter your name broo!");return}
 name=n;localStorage.setItem('storkie_name',name);
 localStorage.setItem('storkie_avatar',myAvatar);
 localStorage.setItem('storkie_pic',myPic);
 document.getElementById('setup').style.display='none';
 socket.emit('join',{name:name,avatar:myAvatar,pic:myPic,room:currentRoom});
}
if(name){setTimeout(()=>socket.emit('join',{name:name,avatar:myAvatar,pic:myPic,room:currentRoom}),300)}

function send(){
 let input=document.getElementById('m');
 if(input.value.trim()=="")return;
 socket.emit('message',{name:name,avatar:myAvatar,pic:myPic,text:input.value,room:currentRoom});
 socket.emit('typing',{name:name,room:currentRoom,typing:false});
 input.value="";
}
document.getElementById('file').addEventListener('change',function(){
 let f=this.files[0];if(!f)return;let r=new FileReader();r.onload=()=>{socket.emit('message',{name:name,avatar:myAvatar,pic:myPic,image:r.result,room:currentRoom})};r.readAsDataURL(f);this.value="";
});

let typingTimer;
document.getElementById('m').addEventListener('input',()=>{
 socket.emit('typing',{name:name,room:currentRoom,typing:true});
 clearTimeout(typingTimer);typingTimer=setTimeout(()=>socket.emit('typing',{name:name,room:currentRoom,typing:false}),1000);
});
document.getElementById('m').addEventListener('keypress',e=>{if(e.key=='Enter')send()});

function addMsg(data){
 let div=document.createElement('div');
 div.className='msg'+(data.name==name?' me':'');
 let av=data.pic?'<img src="'+data.pic+'">':data.avatar;
 let content=data.image?'<img class="chat-img" src="'+data.image+'">':'<p>'+(data.text||"")+'</p>';
 let reactsHtml='<div class="reacts"><button onclick="react(&quot;'+data.id+'&quot;,&quot;❤️&quot;)">❤️ '+(data.reactions?.['❤️']||0)+'</button><button onclick="react(&quot;'+data.id+'&quot;,&quot;😂&quot;)">😂 '+(data.reactions?.['😂']||0)+'</button><button onclick="react(&quot;'+data.id+'&quot;,&quot;🔥&quot;)">🔥 '+(data.reactions?.['🔥']||0)+'</button></div>';
 div.innerHTML='<div class="avatar">'+av+'</div><div><b>'+data.name+'</b><br>'+content+'</div>'+reactsHtml;
 div.id='msg-'+data.id;
 chat.appendChild(div);chat.scrollTop=chat.scrollHeight;
 if(data.name!=name){notify("Storkie - #"+currentRoom, data.name+": "+(data.text||"sent an image"))}
}
function react(id,emoji){socket.emit('react',{id:id,emoji:emoji,room:currentRoom})}

socket.on('history',function(list){chat.innerHTML="";list.forEach(addMsg)});
socket.on('message',function(data){addMsg(data)});
socket.on('online',function(users){
 document.getElementById('onlineCount').textContent=users.length+" Online";
 document.getElementById('onlineList').innerHTML="🟢 "+users.map(u=>u.name).join(" • ");
});
socket.on('typing',function(d){
 let t=document.getElementById('typing');
 if(d.typing && d.name!=name){t.textContent=d.name+" is typing..."}else{t.textContent=""}
});
socket.on('react_update',function(d){
 let el=document.getElementById('msg-'+d.id);
 if(el){let btns=el.querySelectorAll('.reacts button');let ems=["❤️","😂","🔥"];btns.forEach((b,i)=>{b.innerHTML=ems[i]+" "+(d.reactions[ems[i]]||0)})}
});
renderRooms();
</script></body></html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@socketio.on('join')
def on_join(data):
    room = data.get('room','general')
    online[request.sid] = {'name': data.get('name'), 'room': room, 'avatar': data.get('avatar'), 'pic': data.get('pic')}
    join_room(room)
    emit('history', messages.get(room, [])[-100:], room=request.sid)
    emit('online', [u for u in online.values() if u['room']==room], room=room)

@socketio.on('switch_room')
def on_switch(data):
    old = online.get(request.sid, {}).get('room')
    if old: leave_room(old)
    room = data.get('room','general')
    online[request.sid] = {'name': data.get('name'), 'room': room, 'avatar': data.get('avatar'), 'pic': data.get('pic')}
    join_room(room)
    emit('history', messages.get(room, [])[-100:], room=request.sid)
    emit('online', [u for u in online.values() if u['room']==room], room=room)

@socketio.on('message')
def handle_message(data):
    from flask import request
    room = data.get('room','general')
    msg = {'id': str(uuid.uuid4())[:8], 'name': data.get('name'), 'avatar': data.get('avatar'), 'pic': data.get('pic'), 'text': data.get('text',''), 'image': data.get('image',''), 'room': room, 'time': time.time(), 'reactions': {}}
    messages.setdefault(room, []).append(msg)
    messages[room] = messages[room][-200:]
    save()
    emit('message', msg, room=room)

@socketio.on('typing')
def on_typing(data):
    emit('typing', data, room=data.get('room','general'), include_self=False)

@socketio.on('react')
def on_react(data):
    room = data.get('room','general')
    for m in messages.get(room, []):
        if m['id']==data.get('id'):
            m['reactions'][data['emoji']] = m['reactions'].get(data['emoji'],0)+1
            save()
            emit('react_update', {'id': m['id'], 'reactions': m['reactions']}, room=room)
            break

@socketio.on('disconnect')
def on_disc():
    from flask import request
    u = online.pop(request.sid, None)
    if u:
        emit('online', [x for x in online.values() if x['room']==u['room']], room=u['room'])

from flask import request

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
