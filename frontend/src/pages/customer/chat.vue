<template>
  <div class="consumer-chat">
    <header class="chat-toolbar">
      <div class="chat-toolbar-copy">
        <p class="chat-toolbar-kicker">ChatGPT Mirror</p>
        <h1 class="chat-toolbar-title">{{ messages.length ? '当前对话' : '准备开始一段新对话' }}</h1>
      </div>

      <div class="chat-toolbar-actions">
        <div v-if="statusMessage" class="chat-status-pill" :class="sessionSummary.available ? 'info' : 'warn'">
          {{ statusMessage }}
        </div>

        <button class="control-button" type="button" :disabled="pending" @click="resetConversation">新聊天</button>
      </div>
    </header>

    <section class="chat-stage">
      <div v-if="!messages.length" class="chat-empty">
        <p class="empty-kicker">{{ welcomeLabel }}</p>
        <h2 class="empty-title">今天想聊点什么？</h2>
        <p class="empty-copy">
          登录后直接调用后台已配置账号，无需再次填写 Access Token、Session Token 或 Refresh Token。
        </p>

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
          <div class="message-inner">
            <span class="message-avatar">{{ item.role === 'user' ? '你' : 'AI' }}</span>

            <div class="message-body">
              <div class="message-meta">
                <span>{{ item.role === 'user' ? '你' : 'ChatGPT Mirror' }}</span>
                <span v-if="item.role === 'assistant' && item.accountLabel">{{ item.accountLabel }}</span>
              </div>

              <div class="message-bubble" :class="{ pending: item.pending }">
                <p class="message-content">{{ item.content || (item.pending ? '正在生成回复…' : '暂无内容') }}</p>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="composer-shell">
      <div class="composer-surface" :class="{ busy: pending, disabled: !sessionSummary.available }">
        <textarea
          v-model="draft"
          class="composer-input"
          rows="1"
          placeholder="给 ChatGPT Mirror 发送消息"
          :disabled="!sessionSummary.available || pending"
          @keydown="handleComposerKeydown"
        ></textarea>

        <div class="composer-footer">
          <div class="composer-meta">
            <label class="composer-select-shell">
              <span>模型</span>
              <select v-model="selectedModel" class="composer-select" :disabled="pending || !sessionSummary.available">
                <option v-for="item in modelOptions" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>

            <span class="composer-chip">{{ currentModelLabel }}</span>
            <span class="composer-chip">{{ currentAccountLabel }}</span>
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
  consumeConsumerComposeState,
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

const loadSessionSummary = async (preferredModel = '') => {
  const response = await RequestApi('/0x/user/session-summary');
  if (!response.ok) return;

  sessionSummary.value = await response.json();
  modelOptions.value = uniqModelOptions([...sessionSummary.value.supported_models, ...defaultConsumerModels]);

  if (preferredModel && modelOptions.value.includes(preferredModel)) {
    selectedModel.value = preferredModel;
  } else if (!selectedModel.value || !modelOptions.value.includes(selectedModel.value)) {
    selectedModel.value = modelOptions.value[0] || 'gpt-5.4';
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
  const pendingCompose = consumeConsumerComposeState();
  await loadSessionSummary(pendingCompose?.model || '');
  await refreshChatEntry();
  if (pendingCompose?.prompt && sessionSummary.value.available) {
    draft.value = pendingCompose.prompt;
    updateComputedState();
    await sendMessage();
  }
});
</script>

<style scoped lang="less">
.consumer-chat {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 16px;
  min-height: calc(100vh - 36px);
}

.chat-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 6px 8px 0;
}

.chat-toolbar-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.chat-toolbar-kicker,
.empty-kicker {
  margin: 0;
  color: #8b8b84;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.chat-toolbar-title {
  margin: 0;
  font-size: clamp(26px, 3vw, 34px);
  font-weight: 700;
  letter-spacing: -0.04em;
}

.chat-toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.chat-status-pill {
  display: inline-flex;
  align-items: center;
  max-width: min(520px, 100%);
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
}

.chat-status-pill.info {
  background: rgba(233, 239, 235, 0.92);
  color: #32513f;
}

.chat-status-pill.warn {
  background: rgba(252, 239, 221, 0.96);
  color: #8a5327;
}

.chat-stage {
  min-height: 0;
  overflow: hidden;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  min-height: 100%;
  padding: 36px 20px;
  text-align: center;
  background:
    radial-gradient(circle at top center, rgba(255, 255, 255, 0.98), rgba(245, 245, 242, 0.98) 58%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.72) 0%, rgba(245, 245, 242, 0.86) 100%);
  border-radius: 32px;
}

.empty-title {
  max-width: 12ch;
  margin: 0;
  font-size: clamp(40px, 6vw, 64px);
  font-weight: 700;
  line-height: 0.94;
  letter-spacing: -0.05em;
}

.empty-copy {
  max-width: 54ch;
  margin: 0;
  color: #666661;
  font-size: 15px;
  line-height: 1.75;
}

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: min(920px, 100%);
  margin-top: 10px;
}

.prompt-pill,
.control-button,
.ghost-action,
.send-action {
  min-height: 44px;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  color: #171717;
  font: inherit;
}

.prompt-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 6px;
  padding: 16px;
  text-align: left;
  box-shadow:
    0 18px 36px rgba(17, 17, 17, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  cursor: pointer;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.prompt-pill:hover,
.control-button:hover,
.ghost-action:hover,
.send-action:hover {
  transform: translateY(-1px);
  border-color: rgba(17, 17, 17, 0.12);
}

.prompt-pill span {
  font-size: 14px;
  font-weight: 700;
}

.prompt-pill small {
  color: #73736c;
  font-size: 12px;
  line-height: 1.6;
}

.control-button,
.ghost-action,
.send-action {
  padding: 0 18px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease;
}

.message-viewport {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  padding: 8px 0;
  animation: fade-in 0.22s ease;
}

.message-row {
  display: flex;
  justify-content: center;
  padding: 0 8px;
  animation: rise-in 0.24s ease;
}

.message-inner {
  display: flex;
  gap: 16px;
  width: min(860px, 100%);
}

.message-row.user .message-inner {
  flex-direction: row-reverse;
}

.message-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  color: #171717;
  font-size: 12px;
  font-weight: 700;
}

.message-row.user .message-avatar {
  border-color: transparent;
  background: #171717;
  color: #fff;
}

.message-body {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 8px;
}

.message-row.user .message-body {
  align-items: flex-end;
}

.message-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #8a8a84;
  font-size: 12px;
  font-weight: 600;
}

.message-bubble {
  width: fit-content;
  max-width: min(100%, 720px);
  padding: 18px 20px;
  border: 1px solid rgba(17, 17, 17, 0.06);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
    0 16px 30px rgba(17, 17, 17, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.message-row.user .message-bubble {
  border-color: transparent;
  background: #1d1d1d;
  color: #fff;
  box-shadow: 0 16px 30px rgba(17, 17, 17, 0.08);
}

.message-bubble.pending {
  position: relative;
}

.message-bubble.pending::after {
  content: '';
  position: absolute;
  right: 18px;
  bottom: 12px;
  width: 34px;
  height: 3px;
  border-radius: 999px;
  background: rgba(17, 17, 17, 0.12);
}

.message-row.user .message-bubble.pending::after {
  background: rgba(255, 255, 255, 0.24);
}

.message-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 15px;
  line-height: 1.8;
}

.composer-shell {
  position: sticky;
  bottom: 0;
  padding-top: 10px;
  background: linear-gradient(180deg, rgba(245, 245, 242, 0) 0%, rgba(245, 245, 242, 0.9) 24%, #f5f5f2 100%);
}

.composer-surface {
  padding: 14px;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow:
    0 24px 60px rgba(17, 17, 17, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.composer-surface.busy {
  box-shadow:
    0 24px 60px rgba(17, 17, 17, 0.08),
    inset 0 0 0 1px rgba(17, 17, 17, 0.05);
}

.composer-surface.disabled {
  opacity: 0.78;
}

.composer-input {
  width: 100%;
  min-height: 108px;
  padding: 10px 8px 16px;
  border: 0;
  background: transparent;
  color: #171717;
  font: inherit;
  font-size: 16px;
  line-height: 1.75;
  resize: vertical;
  outline: none;
}

.composer-footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
}

.composer-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.composer-select-shell,
.composer-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 999px;
  background: rgba(247, 247, 244, 0.96);
  color: #5f5f59;
  font-size: 12px;
  font-weight: 600;
}

.composer-select-shell span {
  color: #7a7a74;
}

.composer-select {
  min-width: 132px;
  border: 0;
  background: transparent;
  color: #171717;
  font-size: 13px;
  font-weight: 700;
  outline: none;
}

.composer-actions {
  display: flex;
  gap: 10px;
}

.ghost-action {
  background: rgba(255, 255, 255, 0.96);
}

.send-action {
  border-color: #171717;
  background: #171717;
  color: #fff;
}

.control-button:disabled,
.ghost-action:disabled,
.send-action:disabled,
.composer-select:disabled,
.composer-input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
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
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .chat-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .chat-toolbar-actions {
    width: 100%;
    justify-content: space-between;
  }

  .prompt-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .consumer-chat {
    min-height: calc(100vh - 28px);
  }

  .chat-toolbar,
  .message-row {
    padding-left: 0;
    padding-right: 0;
  }

  .empty-title {
    max-width: none;
    font-size: 40px;
  }

  .message-inner {
    gap: 12px;
  }

  .message-bubble {
    max-width: 100%;
  }

  .composer-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .composer-actions {
    justify-content: flex-end;
  }
}

@media (max-width: 640px) {
  .chat-status-pill {
    max-width: none;
    width: 100%;
  }

  .chat-toolbar-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .control-button,
  .ghost-action,
  .send-action {
    width: 100%;
  }

  .message-avatar {
    flex-basis: 30px;
    width: 30px;
    height: 30px;
    border-radius: 10px;
  }

  .composer-select-shell,
  .composer-chip {
    width: 100%;
    justify-content: space-between;
  }

  .composer-select {
    min-width: 0;
    text-align: right;
  }
}
</style>
