const socket = io("http://127.0.0.1:5000"); // Backend server URL
socket.on("connect", () => {
  console.log("✅ Socket.IO connected to backend!");
});

function displayMessage(message, sender = "bot") {
  const chatBox = document.getElementById("chat-box");
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("chat-message", sender + "-message");
  messageDiv.innerHTML = `<p>${message}</p>`;
  chatBox.appendChild(messageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function sendMessage() {
  const userInput = document.getElementById("user-input").value;
  if (!userInput.trim()) return;
  displayMessage(userInput, "user");
  socket.emit("user_message", userInput);
  document.getElementById("user-input").value = "";
}

socket.on("bot_response", (data) => {
  displayMessage(data.message, "bot");
});

function appendProteinViewerButton(uniprotId) {
  const chatBox = document.getElementById("chat-box");
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-message bot-message";
  msgDiv.innerHTML = `
    <p>🔍 Here's the 3D structure for <b>${uniprotId}</b>:</p>
    <button onclick="viewStructure('${uniprotId}')">🔬 View 3D Structure</button>
  `;
  chatBox.appendChild(msgDiv);
}
