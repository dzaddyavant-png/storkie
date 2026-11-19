from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'storkie-secret-v2'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Storkie 🐦</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
body{font-family:Arial;background:#e8f5e9;margin:0;padding:0}
header{background:#075E54;color:white;padding:14px;text-align:center;font-size:22px;font-weight:bold;position:sticky;top:0}
header small{font-size:12px;opacity:0.8;display:block}
#chat{height:calc(100vh - 140px);overflow-y:auto;padding:10px}
.msg{background:white;padding:10px;border-radius:14px;margin:8px 0;max-width:85%;display:flex;gap:8px;box-shadow:0 1px 2px rgba(0,0,0,0.1)}
.me{background:#dcf8c6;margin-left:auto;flex-direction:row-reverse}
.avatar{width:38px;height:38px;border-radius:50%;background:#25D366;color:white;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;overflow:hidden}
.avatar img{width:100%;height:100%;object-fit:cover}
.msg b{font-size:13px;color:#075E54}
.msg p{margin:3px 0 0 0;font-size:15px;word-break:break-word}
.msg img.chat-img{max-width:100%;border-radius:10px;margin-top:5px;display:block}
#box{display:flex;padding:10px;background:white;gap:6px;align-items:center;position:fixed;bottom:0;left:0;right:0}
input#m{flex:1;padding:12px;border-radius:20px;border:1px solid #ccc;outline:none}
button{background:#25D366;color:white;border:none;padding:12px 16px;border-radius:20px;font-weight:bold;cursor:pointer}
#imgBtn{background:#eee;color:#333}
#setup{position:fixed;inset:0;background:#075E54;color:white;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;z-index:99;text-align:center}
#setup input{padding:12px;border-radius:20px;border:none;width:100%;max-width:300px;margin:8px 0;text-align:center;font-size:16px}
#setup button{width:100%;max-width:300px;padding:13px}
.avatars{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap;justify-content:center}
.avatars span{font-size:26px;background:rgba(255,255,255,0.2);padding:8px;border-radius:50%;cursor:pointer}
.avatars span.sel{outline:3px solid white}
#myPic{width:70px;height:70px;border-radius:50%;background:white;display:flex;align-items:center;justify-content:center;font-size:35px;overflow:hidden;margin-bottom:5px}
#myPic img{width:100%;height:100%;object-fit:cover}
</style>
</head>
<body>
<header>🐦 Storkie <small>Chat with your people • Online</small></header>
<div id="chat"></div>
<div id="box">
<label for="file" id="imgBtn" style="padding:12px 14px;border-radius:20px;cursor:pointer">📷</label>
<input type="file" id="file" accept="image/*" hidden>
<input id="m" placeholder="Type a message...">
<button onclick="send()">Send ➤</button>
</div>

<div id="setup">
<div id="myPic">🐦</div>
<h2 style="margin:5px">Welcome to Storkie!</h2>
<p>Pick a name & avatar</p>
<input id="nameInput" placeholder="Your name... e.g Dzaddy">
<div class="avatars" id="avatarList"></div>
<input type="file" id="picInput" accept="image/*" style="background:white;color:black">
<p style="font-size:12px;opacity:0.8">Optional: Upload your profile pic</p>
<button onclick="join()">Join Storkie ➤</button>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
let name = localStorage.getItem('storkie_name') || "";
let myAvatar = localStorage.getItem('storkie_avatar') || "🐦";
let myPic = localStorage.getItem('storkie_pic') || "";
let socket = io();
let chat = document.getElementById('chat');
let emojis = ["🐦","😎","🔥","🦁","👑","💎","⚽","🎮","😂","🌟","🐺","🦅"];
let avDiv = document.getElementById('avatarList');
emojis.forEach(e=>{
  let s=document.createElement('span'); s.textContent=e;
  if(e==myAvatar) s.classList.add('sel');
  s.onclick=()=>{ myAvatar=e; document.querySelectorAll('.avatars span').forEach(x=>x.classList.remove('sel')); s.classList.add('sel'); document.getElementById('myPic').innerHTML=e; };
  avDiv.appendChild(s);
});
if(myPic){ document.getElementById('myPic').innerHTML='<img src="'+myPic+'">'; }
document.getElementById('picInput').addEventListener('change', function(){
  let f=this.files[0]; if(!f) return;
  let r=new FileReader(); r.onload=()=>{ myPic=r.result; document.getElementById('myPic').innerHTML='<img src="'+myPic+'">'; }; r.readAsDataURL(f);
});
if(name){ document.getElementById('setup').style.display='none'; }
else { document.getElementById('nameInput').value=""; }

function join(){
  let n=document.getElementById('nameInput').value.trim();
  if(!n){ alert("Enter your name broo!"); return; }
  name=n; localStorage.setItem('storkie_name',name);
  localStorage.setItem('storkie_avatar',myAvatar);
  localStorage.setItem('storkie_pic',myPic);
  document.getElementById('setup').style.display='none';
}
function send(){
  let input=document.getElementById('m');
  if(input.value.trim()=="") return;
  socket.emit('message',{name:name,avatar:myAvatar,pic:myPic,text:input.value});
  input.value="";
}
document.getElementById('file').addEventListener('change', function(){
  let f=this.files[0]; if(!f) return;
  let r=new FileReader(); r.onload=()=>{ socket.emit('message',{name:name,avatar:myAvatar,pic:myPic,image:r.result}); }; r.readAsDataURL(f);
  this.value="";
});
socket.on('message', function(data){
  let div=document.createElement('div');
  div.className='msg'+(data.name==name?' me':'');
  let av = data.pic ? '<img src="'+data.pic+'">' : data.avatar;
  let content = data.image ? '<img class="chat-img" src="'+data.image+'">' : '<p>'+data.text+'</p>';
  div.innerHTML='<div class="avatar">'+av+'</div><div><b>'+data.name+'</b><br>'+content+'</div>';
  chat.appendChild(div); chat.scrollTop=chat.scrollHeight;
});
document.getElementById('m').addEventListener('keypress', e=>{ if(e.key=='Enter') send(); });
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@socketio.on('message')
def handle_message(data):
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
