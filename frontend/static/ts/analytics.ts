declare const Auth: {
  requireAuth(): boolean;
};

declare const API: {
  get(path: string): Promise<any>;
  post(path: string, body?: any): Promise<any>;
};

declare const Toast: {
  info(message: string): void;
};

declare const marked: (text: string) => string;

declare const Plotly: {
  newPlot(id: string, data: any[], layout: any, opts?: any): void;
};

declare function confirmAction(message: string, callback: () => void): void;

interface ChatItem {
  answer?: string | null;
  interaction_id: string;
}

interface ChatResponse {
  ok: boolean;
  message?: string;
  data?: {
    interaction_id: string;
    graphs?: any[];
  };
  detail?: string;
}

interface HistoryResponse {
  ok: boolean;
  status: number;
  data?: {
    history: ChatItem[];
  };
}

let isSending: boolean = false;
let currentThinkBlock: HTMLElement | null = null;
let lastInteractionId: string | null = null;

document.addEventListener("DOMContentLoaded", (): void => {
  if (!Auth.requireAuth()) return;

  loadSessionGraphs();
  loadChatHistory();

  const input = document.getElementById(
    "chat-input",
  ) as HTMLTextAreaElement | null;
  input?.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  input?.addEventListener("input", (): void => {
    if (!input) return;
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });

  document.getElementById("send-btn")?.addEventListener("click", sendMessage);
  document.getElementById("stop-btn")?.addEventListener("click", stopQuery);
  document
    .getElementById("clear-graphs-btn")
    ?.addEventListener("click", clearAllGraphs);
});

const loadChatHistory = async (): Promise<void> => {
  const res = (await API.get("/api/chat/history")) as HistoryResponse | null;
  if (!res?.ok) return;

  const history = res.data?.history || [];
  history.forEach((item: ChatItem) => {
    if (!item) return;
    const answer = item.answer == null ? "" : String(item.answer);
    if (answer === "") return;
    appendBotMessage(answer, item.interaction_id, false);
  });
};

const sendMessage = async (): Promise<void> => {
  if (isSending) return;

  const input = document.getElementById(
    "chat-input",
  ) as HTMLTextAreaElement | null;
  const message = input?.value.trim();
  if (!message) return;

  isSending = true;
  if (input) input.value = "";
  if (input) input.style.height = "auto";
  setUIState("sending");
  appendUserMessage(message);

  currentThinkBlock = appendThinkingBlock();

  try {
    const res = (await API.post("/api/chat", {
      message,
    })) as ChatResponse | null;

    finalizeThinkingBlock(currentThinkBlock, res?.ok ?? false);
    currentThinkBlock = null;

    if (!res) {
      appendBotMessage("Connection lost. Please try again.");
      return;
    }

    if (res.ok) {
      const answer = res.message || "No response.";
      lastInteractionId = res.data?.interaction_id || null;
      appendBotMessage(answer, lastInteractionId ?? "", true);
      if (res.data?.graphs?.length) renderGraphs(res.data.graphs);
    } else {
      appendBotMessage(res.detail || res.message || "An error occurred.");
    }
  } catch (err) {
    finalizeThinkingBlock(currentThinkBlock, false);
    currentThinkBlock = null;
    appendBotMessage("Network error. Please check your connection.");
  } finally {
    isSending = false;
    setUIState("idle");
    scrollToBottom();
  }
};

const stopQuery = async (): Promise<void> => {
  const stopBtn = document.getElementById(
    "stop-btn",
  ) as HTMLButtonElement | null;
  if (stopBtn) stopBtn.disabled = true;
  await API.post("/api/chat/stop");
  Toast.info("Stop signal sent — the agent will finish its current step.");
};

const setUIState = (state: "sending" | "idle"): void => {
  const sendBtn = document.getElementById(
    "send-btn",
  ) as HTMLButtonElement | null;
  const stopBtn = document.getElementById(
    "stop-btn",
  ) as HTMLButtonElement | null;
  const status = document.getElementById("status-text");

  if (state === "sending") {
    if (sendBtn) sendBtn.style.display = "none";
    if (stopBtn) {
      stopBtn.style.display = "flex";
      stopBtn.disabled = false;
    }
    if (status) status.textContent = "Thinking…";
  } else {
    if (sendBtn) sendBtn.style.display = "flex";
    if (stopBtn) stopBtn.style.display = "none";
    if (status) status.textContent = "";
  }
};

const appendUserMessage = (text: string): HTMLElement => {
  const box = document.getElementById("chat-messages");
  const el = document.createElement("div");
  el.className = "msg user";
  el.innerHTML = `
    <div class="msg-avatar">You</div>
    <div class="msg-bubble">${escHtml(text)}</div>`;
  box?.appendChild(el);
  scrollToBottom();
  return el;
};

const appendThinkingBlock = (): HTMLElement => {
  const box = document.getElementById("chat-messages");
  const wrapper = document.createElement("div");
  wrapper.className = "msg bot";
  wrapper.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div style="flex:1">
      <div class="thinking-block" id="think-${Date.now()}">
        <div class="thinking-header" onclick="toggleThinking(this)">
          <div class="thinking-pulse" id="think-pulse"></div>
          <span class="thinking-label">Reasoning</span>
          <span class="thinking-toggle">▾ collapse</span>
        </div>
        <div class="thinking-steps" id="think-steps"></div>
      </div>
    </div>`;
  box?.appendChild(wrapper);
  scrollToBottom();
  simulateThinking(wrapper);
  return wrapper;
};

const appendBotMessage = (
  text: string,
  interactionId: string = "",
  final: boolean = false,
): HTMLElement => {
  const box = document.getElementById("chat-messages");
  const el = document.createElement("div");
  el.className = "msg bot";
  el.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-bubble" ${interactionId ? `data-interaction-id="${interactionId}"` : ""}>
      <div class="msg-markdown">${marked(text)}</div>
      ${final ? '<button class="msg-regenerate-btn" onclick="regenerateMessage(this)"><i class="fas fa-redo"></i></button>' : ""}
    </div>`;
  box?.appendChild(el);
  scrollToBottom();
  return el;
};

const finalizeThinkingBlock = (
  wrapper: HTMLElement | null,
  success: boolean,
): void => {
  if (!wrapper) return;
  const block = wrapper.querySelector(".thinking-block");
  if (block) {
    block.classList.toggle("done", success);
    block.classList.toggle("error", !success);
  }
  const pulse = wrapper.querySelector(".thinking-pulse");
  if (pulse) pulse.remove();
};

const toggleThinking = (header: HTMLElement): void => {
  const block = header.closest(".thinking-block");
  if (block) block.classList.toggle("collapsed");
};

const regenerateMessage = async (btn: HTMLElement): Promise<void> => {
  const bubble = btn.closest(".msg-bubble");
  const interactionId = bubble?.getAttribute("data-interaction-id");
  if (!interactionId) return;

  const res = await API.post("/api/chat/regenerate", {
    interaction_id: interactionId,
  });
  if (res?.ok) {
    const answer = res.message || "Regenerated response.";
    const markdown = bubble?.querySelector(".msg-markdown");
    if (markdown) markdown.innerHTML = marked(answer);
  }
};

const renderGraphs = (graphs: any[]): void => {
  const container = document.getElementById("graphs-container");
  if (!container) return;

  graphs.forEach((graph: any) => {
    const div = document.createElement("div");
    div.className = "graph-item";
    div.id = `graph-${graph.id}`;
    container.appendChild(div);
    Plotly.newPlot(`graph-${graph.id}`, graph.data, graph.layout, {
      responsive: true,
    });
  });
};

const clearAllGraphs = (): void => {
  confirmAction("Clear all graphs?", () => {
    const container = document.getElementById("graphs-container");
    if (container) container.innerHTML = "";
  });
};

const loadSessionGraphs = async (): Promise<void> => {
  const res = await API.get("/api/graphs/session");
  if (res?.ok && res.data?.graphs) {
    renderGraphs(res.data.graphs);
  }
};

const scrollToBottom = (): void => {
  const box = document.getElementById("chat-messages");
  if (box) box.scrollTop = box.scrollHeight;
};

const escHtml = (text: string): string => {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
};

const simulateThinking = (_wrapper: HTMLElement): void => {};
