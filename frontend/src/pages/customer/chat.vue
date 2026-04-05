<template>
  <div class="consumer-chat">
    <section class="chat-header">
      <div class="chat-heading">
        <p class="chat-kicker">Workspace</p>
        <h1 class="chat-title">登录后直接开始对话</h1>
        <p class="chat-copy">系统会自动调用后台已配置的官方账号或中转账号，用户无需再次登录或填写任何 Token。</p>
      </div>

      <div class="chat-controls">
        <label class="control-field">
          <span>模型</span>
          <select v-model="selectedModel" class="control-select" :disabled="pending">
            <option v-for="item in modelOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>

        <button class="control-button" type="button" :disabled="pending" @click="resetConversation">新对话</button>
      </div>
    </section>

    <div v-if="statusMessage" class="chat-banner" :class="sessionSummary.available ? 'info' : 'warn'">
      {{ statusMessage }}
    </div>

    <section class="chat-stage">
      <div v-if="!messages.length" class="chat-empty">
        <p class="empty-kicker">{{ welcomeLabel }}</p>
        <h2 class="empty-title">可以直接像 ChatGPT 一样开始提问</h2>
        <p class="empty-copy">后台会根据你当前套餐、可用账号和模型支持情况自动调度到合适通道。</p>

        <div class="prompt-grid">
          <button v-for="item in promptIdeas" :key="item.label" class="prompt-pill" type="button" @click="applyPrompt(item.prompt)">
            <span>{{ item.label }}</span>
            <small>{{ item.prompt }}</small>
          </button>
        </div>
      </div>

      <div v-else ref="messageViewportRef" class="message-viewport">
        <article
          v-for="item in messages"
          :key="item.id"
          class="message-row"
          :class="item.role === 'user' ? 'user' : 'assistant'"
        >
          <div class="message-meta">
            <span>{{ item.role === 'user' ? '你' : 'AI' }}</span>
            <span v-if="item.role === 'assistant' && item.accountLabel">{{ item.accountLabel }}</span>
          </div>
          <div class="message-bubble" :class="{ pending: item.pending }">
            <p class="message-content">{{ item.content || (item.pending ? '正在生成回复…' : '暂无内容') }}</p>
          </div>
        </article>
      </div>
    </section>

    <section class="composer-shell">
      <div class="composer-surface" :class="{ busy: pending }">
        <textarea
          v-model="draft"
          class="composer-input"
          rows="1"
          placeholder="输入你的问题，按 Enter 发送，Shift + Enter 换行"
          :disabled="!sessionSummary.available || pending"
          @keydown="handleComposerKeydown"
        ></textarea>

        <div class="composer-footer">
          <div class="composer-status">
            <span>{{ currentAccountLabel }}</span>
            <span>{{ currentModelLabel }}</span>
          </div>

          <div class="composer-actions">
            <button v-if="pending" class="ghost-action" type="button" @click="stopGeneration">停止</button>
            <button class="send-action" type="button" :disabled="!canSend" @click="sendMessage">
              {{ pending ? '生成中…' : '发送' }}
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue';

import RequestApi from '@/api/request';
import {
  defaultConsumerModels,
  getConsumerChatEntry,
  type ConsumerChatEntry,
} from '@/utils/direct-chat';

interface SessionQuotaStatus {
  allowed: boolean;
  reason: string;
  warnings: string[];
}

interface SessionSummary {
  available: boolean;
  reason: string;
  supported_models: string[];
  recommended_account: {
    chatgpt_username: string;
    source_type: string;
  } | null;
  web_quota_status: SessionQuotaStatus;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  pending?: boolean;
  accountLabel?: string;
}

const sessionSummary = ref<SessionSummary>({
  available: false,
  reason: '',
  supported_models: [],
  recommended_account: null,
  web_quota_status: {
    allowed: true,
    reason: '',
    warnings: [],
  },
});
const selectedModel = ref('');
const draft = ref('');
const pending = ref(false);
const messages = ref<ChatMessage[]>([]);
const currentEntry = ref<ConsumerChatEntry | null>(null);
const messageViewportRef = ref<HTMLElement | null>(null);
const activeAbortController = ref<AbortController | null>(null);

const promptIdeas = [
  {
    label: '写一段方案',
    prompt: '帮我写一版针对新用户的产品介绍文案',
  },
  {
    label: '整理信息',
    prompt: '把这个需求拆成 P0 / P1 / P2 的开发任务',
  },
  {
    label: '辅助运营',
    prompt: '帮我生成一版适合朋友圈发布的活动预告',
  },
];

const uniqModelOptions = (items: string[]) => {
  const modelSet = new Set<string>();
  items.forEach((item) => {
    const normalized = String(item || '').trim();
    if (normalized) {
      modelSet.add(normalized);
    }
  });
  return Array.from(modelSet);
};

const modelOptions = ref<string[]>(uniqModelOptions(defaultConsumerModels));

const createMessageId = (role: ChatMessage['role']) => `${role}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;

const formatSourceType = (sourceType: string) => {
  if (sourceType === 'relay') return '中转';
  return '官方';
};

const welcomeLabel = ref('已进入对话工作台');

const statusMessage = ref('');

const currentAccountLabel = ref('系统将在发送时自动分配可用账号');

const currentModelLabel = ref('模型将按当前选择发送');

const canSend = ref(false);

const updateComputedState = () => {
  canSend.value = Boolean(draft.value.trim()) && sessionSummary.value.available && !pending.value;
  currentModelLabel.value = selectedModel.value ? `当前模型：${selectedModel.value}` : '当前模型：自动';
  currentAccountLabel.value = currentEntry.value?.chatgpt_username
    ? `当前通道：${formatSourceType(currentEntry.value.source_type)} · ${currentEntry.value.chatgpt_username}`
    : '当前通道：发送时自动调度';
  welcomeLabel.value = sessionSummary.value.recommended_account?.chatgpt_username
    ? `推荐通道：${formatSourceType(sessionSummary.value.recommended_account.source_type)} · ${sessionSummary.value.recommended_account.chatgpt_username}`
    : '已进入对话工作台';
  statusMessage.value = sessionSummary.value.available
    ? sessionSummary.value.web_quota_status.warnings?.[0] || '当前账号已登录，发送消息后会直接进入会话。'
    : sessionSummary.value.reason || sessionSummary.value.web_quota_status.reason || '当前账号暂未开放网页聊天';
};

const extractContentText = (content: unknown): string => {
  if (typeof content === 'string') {
    return content;
  }

  if (Array.isArray(content)) {
    return content
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }
        if (item && typeof item === 'object') {
          const maybeText = (item as { text?: string }).text;
          if (typeof maybeText === 'string') {
            return maybeText;
          }
        }
        return '';
      })
      .join('');
  }

  if (content && typeof content === 'object') {
    const maybeText = (content as { text?: string }).text;
    if (typeof maybeText === 'string') {
      return maybeText;
    }
  }

  return '';
};

const scrollToBottom = async () => {
  await nextTick();
  if (!messageViewportRef.value) return;
  messageViewportRef.value.scrollTop = messageViewportRef.value.scrollHeight;
};

const loadSessionSummary = async () => {
  const response = await RequestApi('/0x/user/session-summary');
  if (!response.ok) return;

  sessionSummary.value = await response.json();
  modelOptions.value = uniqModelOptions([...sessionSummary.value.supported_models, ...defaultConsumerModels]);

  if (!selectedModel.value || !modelOptions.value.includes(selectedModel.value)) {
    selectedModel.value = modelOptions.value[0] || 'gpt-4o-mini';
  }

  updateComputedState();
};

const refreshChatEntry = async () => {
  if (!sessionSummary.value.available) {
    currentEntry.value = null;
    updateComputedState();
    return null;
  }

  const entry = await getConsumerChatEntry(selectedModel.value);
  currentEntry.value = entry;
  updateComputedState();
  return entry;
};

const resetConversation = () => {
  messages.value = [];
  draft.value = '';
  updateComputedState();
};

const applyPrompt = async (prompt: string) => {
  draft.value = prompt;
  updateComputedState();
  await sendMessage();
};

const handleComposerKeydown = async (event: KeyboardEvent) => {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) {
    return;
  }
  event.preventDefault();
  await sendMessage();
};

const stopGeneration = () => {
  activeAbortController.value?.abort();
};

const readErrorMessage = async (response: Response) => {
  try {
    const errorData = await response.json();
    if (errorData?.message) {
      return String(errorData.message);
    }
  } catch (error) {
    console.error(error);
  }
  return '请求失败，请稍后再试';
};

const upsertAssistantText = (messageId: string, nextText: string, append = true) => {
  const assistantMessage = messages.value.find((item) => item.id === messageId);
  if (!assistantMessage) return;
  assistantMessage.content = append ? `${assistantMessage.content}${nextText}` : nextText;
};

const handleStreamPayload = async (payloadText: string, messageId: string) => {
  if (!payloadText || payloadText === '[DONE]') {
    return;
  }

  const payload = JSON.parse(payloadText);
  const choice = payload.choices?.[0];
  const deltaText = extractContentText(choice?.delta?.content);
  const finalText = extractContentText(choice?.message?.content);

  if (deltaText) {
    upsertAssistantText(messageId, deltaText);
    await scrollToBottom();
    return;
  }

  if (finalText) {
    upsertAssistantText(messageId, finalText, false);
    await scrollToBottom();
  }
};

const consumeStream = async (response: Response, messageId: string) => {
  const reader = response.body?.getReader();
  if (!reader) {
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  const flushBuffer = async (force = false) => {
    const lines = buffer.split('\n');
    buffer = force ? '' : lines.pop() || '';

    for (const rawLine of force ? lines : lines) {
      const line = rawLine.trim();
      if (!line.startsWith('data:')) {
        continue;
      }
      const payloadText = line.slice(5).trim();
      if (!payloadText) {
        continue;
      }
      await handleStreamPayload(payloadText, messageId);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    await flushBuffer();
  }

  buffer += decoder.decode();
  await flushBuffer(true);
};

const finishAssistantMessage = (messageId: string) => {
  const assistantMessage = messages.value.find((item) => item.id === messageId);
  if (!assistantMessage) return;
  assistantMessage.pending = false;
  if (!assistantMessage.content.trim()) {
    assistantMessage.content = '本次请求没有返回可展示的文本内容。';
  }
};

const sendMessage = async () => {
  const content = draft.value.trim();
  if (!content || pending.value || !sessionSummary.value.available) {
    return;
  }

  const userMessage: ChatMessage = {
    id: createMessageId('user'),
    role: 'user',
    content,
  };
  messages.value.push(userMessage);

  const requestMessages = messages.value
    .filter((item) => item.role === 'user' || (item.role === 'assistant' && item.content.trim()))
    .map((item) => ({
      role: item.role,
      content: item.content,
    }));

  draft.value = '';
  pending.value = true;
  updateComputedState();

  const assistantMessageId = createMessageId('assistant');
  messages.value.push({
    id: assistantMessageId,
    role: 'assistant',
    content: '',
    pending: true,
  });
  await scrollToBottom();

  try {
    const entry = (await refreshChatEntry()) || currentEntry.value;
    if (!entry) {
      upsertAssistantText(assistantMessageId, '当前账号暂未分配可用的对话通道，请联系管理员。', false);
      finishAssistantMessage(assistantMessageId);
      return;
    }

    const assistantMessage = messages.value.find((item) => item.id === assistantMessageId);
    if (assistantMessage) {
      assistantMessage.accountLabel = `${formatSourceType(entry.source_type)} · ${entry.chatgpt_username}`;
    }

    activeAbortController.value = new AbortController();
    const response = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${entry.token}`,
      },
      body: JSON.stringify({
        model: selectedModel.value,
        messages: requestMessages,
        stream: true,
      }),
      signal: activeAbortController.value.signal,
    });

    if (!response.ok) {
      upsertAssistantText(assistantMessageId, await readErrorMessage(response), false);
      finishAssistantMessage(assistantMessageId);
      return;
    }

    const contentType = response.headers.get('Content-Type') || '';
    if (contentType.includes('text/event-stream')) {
      await consumeStream(response, assistantMessageId);
    } else {
      const payload = await response.json();
      const text = extractContentText(payload.choices?.[0]?.message?.content);
      upsertAssistantText(assistantMessageId, text || '本次请求没有返回可展示的文本内容。', false);
    }
  } catch (error: unknown) {
    if ((error as { name?: string })?.name === 'AbortError') {
      upsertAssistantText(assistantMessageId, '\n\n[已手动停止生成]', true);
    } else {
      console.error(error);
      upsertAssistantText(assistantMessageId, '请求失败，请稍后重试。', false);
    }
  } finally {
    activeAbortController.value = null;
    pending.value = false;
    finishAssistantMessage(assistantMessageId);
    updateComputedState();
    await scrollToBottom();
  }
};

watch([draft, selectedModel, pending], () => {
  updateComputedState();
});

watch(selectedModel, async () => {
  if (!selectedModel.value) return;
  await refreshChatEntry();
});

onMounted(async () => {
  await loadSessionSummary();
  await refreshChatEntry();
});
</script>

<style scoped lang="less">
.consumer-chat {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 16px;
  min-height: calc(100vh - 120px);
}

.chat-header,
.chat-stage,
.composer-shell {
  border: 1px solid rgba(21, 30, 24, 0.08);
  background: rgba(255, 255, 255, 0.72);
  box-shadow:
    0 28px 80px rgba(21, 30, 24, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(18px);
}

.chat-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 28px 30px;
  border-radius: 30px;
}

.chat-kicker,
.empty-kicker {
  margin: 0 0 10px;
  color: #7c8e83;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.chat-title {
  margin: 0;
  font-size: clamp(30px, 4vw, 48px);
  font-weight: 700;
  line-height: 0.96;
  letter-spacing: -0.04em;
}

.chat-copy {
  max-width: 58ch;
  margin: 14px 0 0;
  color: #607166;
  font-size: 15px;
  line-height: 1.7;
}

.chat-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.control-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 180px;
  color: #66786d;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.control-select,
.control-button,
.ghost-action,
.send-action,
.prompt-pill {
  min-height: 46px;
  border: 1px solid rgba(21, 30, 24, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  color: #17221d;
  font: inherit;
}

.control-select {
  padding: 0 14px;
  font-size: 14px;
  font-weight: 600;
}

.control-button,
.ghost-action,
.send-action {
  padding: 0 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    background 0.2s ease;
}

.control-button:hover,
.ghost-action:hover,
.send-action:hover,
.prompt-pill:hover {
  border-color: rgba(21, 30, 24, 0.18);
  transform: translateY(-1px);
}

.chat-banner {
  padding: 14px 18px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.6;
}

.chat-banner.info {
  background: rgba(236, 245, 239, 0.84);
  color: #28523a;
}

.chat-banner.warn {
  background: rgba(253, 244, 231, 0.88);
  color: #84512a;
}

.chat-stage {
  display: flex;
  min-height: 0;
  border-radius: 34px;
  overflow: hidden;
}

.chat-empty,
.message-viewport {
  width: 100%;
  padding: 32px;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 18px;
  min-height: 420px;
  background:
    radial-gradient(circle at top right, rgba(233, 241, 236, 0.92), rgba(255, 255, 255, 0.96) 40%),
    linear-gradient(180deg, #f8f6f1 0%, #fcfcfa 100%);
}

.empty-title {
  max-width: 14ch;
  margin: 0;
  font-size: clamp(34px, 4vw, 52px);
  font-weight: 700;
  line-height: 0.95;
  letter-spacing: -0.04em;
}

.empty-copy {
  max-width: 54ch;
  margin: 0;
  color: #65766b;
  font-size: 15px;
  line-height: 1.7;
}

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.prompt-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 6px;
  padding: 16px;
  text-align: left;
  cursor: pointer;
}

.prompt-pill span {
  font-size: 14px;
  font-weight: 700;
}

.prompt-pill small {
  color: #68796f;
  font-size: 12px;
  line-height: 1.6;
}

.message-viewport {
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
  animation: fade-in 0.24s ease;
}

.message-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  animation: rise-in 0.24s ease;
}

.message-row.user {
  align-items: flex-end;
}

.message-row.assistant {
  align-items: flex-start;
}

.message-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #7a8b81;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.message-bubble {
  max-width: min(820px, 100%);
  padding: 18px 20px;
  border-radius: 24px;
  background: rgba(247, 248, 246, 0.96);
}

.message-row.user .message-bubble {
  background: #17221d;
  color: #fff;
}

.message-bubble.pending {
  position: relative;
}

.message-bubble.pending::after {
  content: '';
  position: absolute;
  inset: auto 20px 12px auto;
  width: 32px;
  height: 2px;
  border-radius: 999px;
  background: rgba(23, 34, 29, 0.12);
}

.message-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 15px;
  line-height: 1.8;
}

.composer-shell {
  padding: 16px;
  border-radius: 28px;
}

.composer-surface {
  padding: 12px;
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(247, 248, 246, 0.96) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.composer-surface.busy {
  box-shadow: inset 0 0 0 1px rgba(21, 30, 24, 0.06);
}

.composer-input {
  width: 100%;
  min-height: 120px;
  padding: 12px 14px;
  border: 0;
  background: transparent;
  color: #17221d;
  font: inherit;
  font-size: 15px;
  line-height: 1.75;
  resize: vertical;
  outline: none;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 0 6px 4px;
}

.composer-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  color: #718178;
  font-size: 12px;
  font-weight: 600;
}

.composer-actions {
  display: flex;
  gap: 10px;
}

.ghost-action {
  background: rgba(255, 255, 255, 0.92);
}

.send-action {
  border-color: #17221d;
  background: #17221d;
  color: #fff;
}

.control-button:disabled,
.control-select:disabled,
.ghost-action:disabled,
.send-action:disabled,
.composer-input:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

@keyframes rise-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .chat-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .chat-controls {
    width: 100%;
    justify-content: flex-start;
  }

  .prompt-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .consumer-chat {
    min-height: auto;
  }

  .chat-header,
  .chat-empty,
  .message-viewport {
    padding: 22px;
  }

  .chat-title,
  .empty-title {
    max-width: none;
  }

  .composer-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .composer-actions {
    justify-content: flex-end;
  }
}
</style>
