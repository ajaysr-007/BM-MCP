// BotIQ Frontend Chatbot Client Configuration
const API_BASE = "http://localhost:8000";

// App state
let clientId = null;
let codeVerifier = null;
let codeChallenge = null;
let tempUserId = null;
let currentStep = "INITIALIZING"; // INITIALIZING -> AWAITING_USER_ID -> AWAITING_PASSWORD -> AUTHENTICATING -> COMPLETED

// Elements
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const resetBtn = document.getElementById("resetBtn");

// Initialize application on load
window.addEventListener("DOMContentLoaded", async () => {
    addBotMessage("System connecting... Please wait.");
    showTypingIndicator();
    
    try {
        // 1. Silent OAuth client registration
        clientId = await registerClient();
        
        // 2. Generate local PKCE keys
        codeVerifier = generateCodeVerifier();
        codeChallenge = await generateCodeChallenge(codeVerifier);
        
        hideTypingIndicator();
        addBotMessage("Hi! Please enter your BotIQ User ID to validate your credentials.");
        currentStep = "AWAITING_USER_ID";
    } catch (err) {
        hideTypingIndicator();
        addSystemMessage("❌ Initialization failed: " + err.message);
        addBotMessage("Failed to connect to the backend. Please check if the MCP server is running and reload the page.");
    }
});

// Event Listeners
chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const val = userInput.value.trim();
    if (!val) return;

    userInput.value = "";
    
    if (currentStep === "AWAITING_USER_ID") {
        addUserMessage(val);
        tempUserId = val;
        
        // Change input to password type for safety
        userInput.type = "password";
        userInput.placeholder = "Enter your Password...";
        currentStep = "AWAITING_PASSWORD";
        
        addBotMessage("Please enter your Password.");
    } 
    else if (currentStep === "AWAITING_PASSWORD") {
        // Obfuscate password in chat log
        addUserMessage("••••••••");
        
        // Revert input back to normal text
        userInput.type = "text";
        userInput.placeholder = "Type a message...";
        
        const password = val;
        currentStep = "AUTHENTICATING";
        
        await runAuthFlow(tempUserId, password);
    }
});

resetBtn.addEventListener("click", () => {
    // Reset all parameters in-memory and reload
    clientId = null;
    codeVerifier = null;
    codeChallenge = null;
    tempUserId = null;
    currentStep = "INITIALIZING";
    chatMessages.innerHTML = "";
    window.location.reload();
});

// OAuth Operations

async function registerClient() {
    console.log("Registering OAuth client dynamically...");
    const resp = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        body: JSON.stringify({
            client_name: "BotIQ Chatbot Demo",
            redirect_uris: ["http://localhost:9000/callback"] // Demo callback
        })
    });
    
    if (!resp.ok) {
        throw new Error("Client registration rejected: Status " + resp.status);
    }
    const data = await resp.json();
    console.log("Client registered successfully. Client ID:", data.client_id);
    return data.client_id;
}

async function runAuthFlow(userId, password) {
    showTypingIndicator();
    addSystemMessage("🔑 Initiating OAuth Authorization Flow...");
    
    try {
        const state = generateState();
        
        // 1. Request Authorization Code via POST
        // We set 'Accept: application/json' to tell the backend to return JSON directly instead of standard HTML RedirectResponse
        const authFormData = new URLSearchParams();
        authFormData.append("client_id", clientId);
        authFormData.append("redirect_uri", "http://localhost:9000/callback");
        authFormData.append("code_challenge", codeChallenge);
        authFormData.append("code_challenge_method", "S256");
        authFormData.append("state", state);
        authFormData.append("user_id", userId);
        authFormData.append("password", password);
        
        const authResp = await fetch(`${API_BASE}/authorize`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            },
            body: authFormData
        });
        
        if (!authResp.ok) {
            const errData = await authResp.json().catch(() => ({}));
            throw new Error(errData.detail || "Authentication rejected (Invalid credentials).");
        }
        
        const authData = await authResp.json();
        const authCode = authData.code;
        console.log("Authorization Code retrieved:", authCode);
        addSystemMessage("🔄 Authorization Code exchanged. Swapping for JWT tokens...");

        // 2. Exchange Authorization Code for JWT tokens (POST /token)
        const tokenFormData = new URLSearchParams();
        tokenFormData.append("grant_type", "authorization_code");
        tokenFormData.append("client_id", clientId);
        tokenFormData.append("code", authCode);
        tokenFormData.append("code_verifier", codeVerifier);

        const tokenResp = await fetch(`${API_BASE}/token`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            },
            body: tokenFormData
        });

        if (!tokenResp.ok) {
            const errData = await tokenResp.json().catch(() => ({}));
            throw new Error(errData.detail || "Token exchange failed.");
        }

        const tokenData = await tokenResp.json();
        const accessToken = tokenData.access_token;
        console.log("JWT Access Token issued successfully.");
        addSystemMessage("✅ JWT Access Token acquired successfully. Starting MCP validation...");

        // 3. Connect to MCP via SSE & call validate_user tool
        await executeMcpToolCall(accessToken, userId, password);

    } catch (err) {
        hideTypingIndicator();
        addErrorMessage(err.message);
        addBotMessage("Please type your BotIQ User ID again to retry.");
        currentStep = "AWAITING_USER_ID";
    }
}

async function executeMcpToolCall(accessToken, userId, password) {
    addSystemMessage("🔌 Connecting to MCP Server SSE Endpoint...");
    
    // We pass the token in the query params since standard EventSource does not support custom headers
    const eventSource = new EventSource(`${API_BASE}/mcp/sse?token=${encodeURIComponent(accessToken)}`);
    let postMessagesUrl = null;

    eventSource.addEventListener("endpoint", async (event) => {
        // Resolve the messages POST URL sent by the MCP Server SSE connection event
        postMessagesUrl = new URL(event.data, API_BASE).toString();
        console.log("MCP SSE endpoint resolved successfully. POST URL:", postMessagesUrl);
        addSystemMessage("⚡ Connection established. Calling 'validate_user' tool...");

        try {
            // Trigger the validate_user tool call
            const toolCallBody = {
                jsonrpc: "2.0",
                id: Date.now(),
                method: "tools/call",
                params: {
                    name: "validate_user",
                    arguments: {
                        user_id: userId,
                        password: password
                    }
                }
            };

            const response = await fetch(postMessagesUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": `Bearer ${accessToken}`
                },
                body: JSON.stringify(toolCallBody)
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error("Tool execution failed: Status " + response.status + " - " + text);
            }

            const jsonResponse = await response.json();
            console.log("MCP validate_user response:", jsonResponse);

            if (jsonResponse.error) {
                throw new Error(jsonResponse.error.message || "MCP Tool internal error");
            }

            // Extract the result text
            const toolResult = jsonResponse.result;
            let resultObject = {};
            if (toolResult && toolResult.content && toolResult.content[0]) {
                const textData = toolResult.content[0].text;
                try {
                    resultObject = JSON.parse(textData);
                } catch {
                    resultObject = { status: "error", message: textData };
                }
            }

            hideTypingIndicator();
            eventSource.close();

            if (resultObject.status === "success") {
                addBotMessage("🎉 Login successful!");
                addSystemMessage("🔑 BotIQ Authorize Token: " + resultObject.authorize_token);
                addBotMessage("You are successfully authenticated and your BotIQ session is established.");
                currentStep = "COMPLETED";
            } else {
                throw new Error(resultObject.message || "BotIQ credentials validation failed.");
            }

        } catch (err) {
            eventSource.close();
            hideTypingIndicator();
            addErrorMessage(err.message);
            addBotMessage("Please type your BotIQ User ID again to retry.");
            currentStep = "AWAITING_USER_ID";
        }
    });

    eventSource.onerror = (e) => {
        console.error("SSE Connection Error:", e);
        eventSource.close();
        hideTypingIndicator();
        addErrorMessage("Failed to establish SSE stream. Verify server is running.");
        addBotMessage("Please type your BotIQ User ID again to retry.");
        currentStep = "AWAITING_USER_ID";
    };
}

// Helpers for PKCE & Chat UI

function generateState() {
    return generateCodeVerifier().substring(0, 16);
}

function generateCodeVerifier() {
    const array = new Uint32Array(32);
    window.crypto.getRandomValues(array);
    return Array.from(array, dec => ('0' + dec.toString(16)).substr(-2)).join('');
}

async function generateCodeChallenge(verifier) {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const hash = await window.crypto.subtle.digest("SHA-256", data);
    
    // Base64url encode without padding
    let str = "";
    const bytes = new Uint8Array(hash);
    for (let i = 0; i < bytes.byteLength; i++) {
        str += String.fromCharCode(bytes[i]);
    }
    return btoa(str)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
}

function addBotMessage(text) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble bot";
    bubble.innerText = text;
    chatMessages.appendChild(bubble);
    scrollChat();
}

function addUserMessage(text) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble user";
    bubble.innerText = text;
    chatMessages.appendChild(bubble);
    scrollChat();
}

function addSystemMessage(text) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble system";
    bubble.innerText = text;
    chatMessages.appendChild(bubble);
    scrollChat();
}

function addErrorMessage(text) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble error";
    bubble.innerText = "❌ Error: " + text;
    chatMessages.appendChild(bubble);
    scrollChat();
}

function showTypingIndicator() {
    // Prevent duplicate typing indicators
    if (document.getElementById("typingIndicator")) return;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble bot";
    bubble.id = "typingIndicator";
    bubble.innerHTML = `
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    chatMessages.appendChild(bubble);
    scrollChat();
}

function hideTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
}

function scrollChat() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
