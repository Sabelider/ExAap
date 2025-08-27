// app.js

const videoLocal = document.getElementById('meu-video');
const videoRemoto = document.getElementById('video-remoto');
const botaoChamar = document.getElementById('botao-chamar');
const inputID = document.getElementById('peer-id-alvo');

const peer = new Peer(); // Cria peer com ID aleatório

let minhaStream;

peer.on('open', (id) => {
  alert('Seu ID é: ' + id);
});

// Obtem vídeo e áudio do usuário
navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then((stream) => {
  minhaStream = stream;
  videoLocal.srcObject = stream;
});

// Quando recebe uma chamada
peer.on('call', (call) => {
  call.answer(minhaStream); // Envia a própria stream
  call.on('stream', (remoteStream) => {
    videoRemoto.srcObject = remoteStream;
  });
});

// Quando clica no botão de chamar
botaoChamar.onclick = () => {
  const idRemoto = inputID.value;
  const call = peer.call(idRemoto, minhaStream);
  call.on('stream', (remoteStream) => {
    videoRemoto.srcObject = remoteStream;
  });
};
