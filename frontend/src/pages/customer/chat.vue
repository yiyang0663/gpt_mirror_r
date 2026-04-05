<template>
  <div class="consumer-chat">
    <header class="chat-toolbar">
      <div class="chat-toolbar-copy">
        <p class="chat-toolbar-kicker">ChatGPT Mirror</p>
        <h1 class="chat-toolbar-title">{{ chatTitle }}</h1>
      </div>

      <div class="chat-toolbar-actions">
        <div v-if="statusMessage" class="chat-status-pill" :class="sessionSummary.available ? 'info' : 'warn'">
          {{ statusMessage }}
        </div>

        <button class="control-button" type="button" :disabled="pending" @click="handleNewConversationClick">新聊天</button>
      </div>
    </header>

    <div class="chat-workspace">
      <aside class="history-panel">
        <div class="history-panel-head">
          <div>
            <p class="history-eyebrow">History</p>
            <h2 class="history-title">历史对话</h2>
          </div>

          <button class="history-create" type="button" :disabled="pending" @click="handleNewConversationClick">新建</button>
        </div>

        <div class="history-list">
          <button
            v-for="item in conversations"
            :key="item.id"
            class="history-item"
            :class="{ active: item.id === activeConversationId }"
            type="button"
            :disabled="pending || conversationLoading"
            @click="openConversation(item.id)"
          >
            <div class="history-item-head">
              <strong>{{ item.title || '新对话' }}</strong>
              <span>{{ formatConversationTime(item.updated_time || item.created_time) }}</span>
            </div>

            <p class="history-item-preview">
              {{ item.preview_text || '还没有消息，发送第一条后会自动保存在这里。' }}
            </p>
          </button>

          <div v-if="historyLoading" class="history-empty">正在加载历史对话…</div>
          <div v-else-if="!conversations.length" class="history-empty">历史对话会自动保存到当前账号下。</div>
        </div>
      </aside>

      <div class="chat-main">
        <section class="chat-stage">
          <div v-if="conversationLoading" class="chat-empty loading">正在载入这段对话…</div>

          <div v-else-if="!messages.length" class="chat-empty">
            <p class="empty-kicker">{{ welcomeLabel }}</p>
            <h2 class="empty-title">今天想聊点什么？</h2>
            <p class="empty-copy">
              历史对话会自动保存。登录后直接调用后台已配置账号，无需再次填写 Access Token、Session Token 或
              Refresh Token。
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
              :disabled="!sessionSummary.available || pending || conversationLoading"
              @keydown="handleComposerKeydown"
            ></textarea>

            <div class="composer-footer">
              <div class="composer-meta">
                <label class="composer-select-shell">
                  <span>模型</span>
                  <select
                    v-model="selectedModel"
                    class="composer-select"
                    :disabled="pending || !sessionSummary.available || conversationLoading"
                  >
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

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
  role: 'user' | 'assistant' | 'system';
  content: string;
  pending?: boolean;
  accountLabel?: string;
}

interface ConversationSummary {
  id: number;
  title: string;
  model_name: string;
  preview_text: string;
  message_count: number;
  last_message_at: number;
  created_time: number;
  updated_time: number;
}

interface PersistedConversationMessage {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  account_label: string;
  sequence: number;
  created_time: number;
  updated_time: number;
}

interface ConversationDetail extends ConversationSummary {
  messages: PersistedConversationMessage[];
}

const router = useRouter();
const route = useRoute();

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
const modelOptions = ref<string[]>([]);
const conversations = ref<ConversationSummary[]>([]);
const activeConversationId = ref<number | null>(null);
const historyLoading = ref(false);
const conversationLoading = ref(false);
const lastHandledNewQuery = ref('');

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

const createMessageId = (role: ChatMessage['role']) => `${role}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;

const formatSourceType = (sourceType: string) => {
  if (sourceType === 'relay') return '中转';
  return '官方';
};

const activeConversation = computed(
  () => conversations.value.find((item) => item.id === activeConversationId.value) || null
);

const chatTitle = computed(() => {
  if (activeConversation.value?.title) {
    return activeConversation.value.title;
  }
  return messages.value.length ? '当前对话' : '准备开始一段新对话';
});

const welcomeLabel = computed(() => {
  return sessionSummary.value.recommended_account?.chatgpt_username
    ? `推荐通道：${formatSourceType(sessionSummary.value.recommended_account.source_type)} · ${sessionSummary.value.recommended_account.chatgpt_username}`
    : '已进入对话工作台';
});

const statusMessage = computed(() => {
  return sessionSummary.value.available
    ? sessionSummary.value.web_quota_status.warnings?.[0] || '当前账号已登录，发送消息后会直接进入会话。'
    : sessionSummary.value.reason || sessionSummary.value.web_quota_status.reason || '当前账号暂未开放网页聊天';
});

const currentModelLabel = computed(() => {
  return selectedModel.value ? `当前模型：${selectedModel.value}` : '当前模型：自动';
});

const currentAccountLabel = computed(() => {
  return currentEntry.value?.chatgpt_username
    ? `当前通道：${formatSourceType(currentEntry.value.source_type)} · ${currentEntry.value.chatgpt_username}`
    : '当前通道：发送时自动调度';
});

const canSend = computed(() => {
  return Boolean(draft.value.trim()) && sessionSummary.value.available && !pending.value && !conversationLoading.value;
});

const scrollToBottom = async () => {
  await nextTick();
  if (!messageViewportRef.value) return;
  messageViewportRef.value.scrollTop = messageViewportRef.value.scrollHeight;
};

const formatConversationTime = (timestamp: number) => {
  if (!timestamp) return '刚刚';
  const date = new Date(timestamp * 1000);
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
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

const normalizeConversationQueryId = (value: unknown) => {
  const rawValue = Array.isArray(value) ? value[0] : value;
  const normalized = Number(rawValue);
  return Number.isInteger(normalized) && normalized > 0 ? normalized : null;
};

const syncRouteToConversation = async (conversationId: number | null) => {
  const nextQuery = conversationId ? { conversation: String(conversationId) } : { new: String(Date.now()) };
  const currentConversationId = normalizeConversationQueryId(route.query.conversation);
  const currentNewValue = String(route.query.new || '');

  if (conversationId && currentConversationId === conversationId) {
    return;
  }

  if (!conversationId && currentNewValue) {
    return;
  }

  await router.replace({
    name: 'CustomerChat',
    query: nextQuery,
  });
};

const upsertConversationSummary = (payload: ConversationSummary) => {
  const nextItem = { ...payload };
  const index = conversations.value.findIndex((item) => item.id === payload.id);
  if (index >= 0) {
    conversations.value.splice(index, 1, nextItem);
  } else {
    conversations.value.push(nextItem);
  }
  conversations.value = [...conversations.value].sort((left, right) => {
    if ((right.updated_time || 0) !== (left.updated_time || 0)) {
      return (right.updated_time || 0) - (left.updated_time || 0);
    }
    return right.id - left.id;
  });
};

const hydrateConversation = async (payload: ConversationDetail) => {
  upsertConversationSummary(payload);
  activeConversationId.value = payload.id;
  messages.value = payload.messages.map((item) => ({
    id: `persisted-${item.id}`,
    role: item.role,
    content: item.content,
    accountLabel: item.account_label,
  }));

  const nextOptions = uniqModelOptions([payload.model_name, ...modelOptions.value, ...defaultConsumerModels]);
  modelOptions.value = nextOptions;
  if (payload.model_name && nextOptions.includes(payload.model_name)) {
    selectedModel.value = payload.model_name;
  } else if (!selectedModel.value || !nextOptions.includes(selectedModel.value)) {
    selectedModel.value = nextOptions[0] || 'gpt-5.4';
  }

  await scrollToBottom();
};

const loadSessionSummary = async (preferredModel = '') => {
  const response = await RequestApi('/0x/user/session-summary');
  if (!response.ok) return;

  sessionSummary.value = await response.json();
  modelOptions.value = uniqModelOptions([preferredModel, ...sessionSummary.value.supported_models, ...defaultConsumerModels]);

  if (preferredModel && modelOptions.value.includes(preferredModel)) {
    selectedModel.value = preferredModel;
  } else if (!selectedModel.value || !modelOptions.value.includes(selectedModel.value)) {
    selectedModel.value = modelOptions.value[0] || 'gpt-5.4';
  }
};

const refreshChatEntry = async () => {
  if (!sessionSummary.value.available) {
    currentEntry.value = null;
    return null;
  }

  const entry = await getConsumerChatEntry(selectedModel.value);
  currentEntry.value = entry;
  return entry;
};

const loadConversationList = async () => {
  historyLoading.value = true;
  try {
    const response = await RequestApi('/0x/user/chat-conversations');
    if (!response.ok) return;
    const payload = (await response.json()) as { results?: ConversationSummary[] };
    conversations.value = [...(payload.results || [])].sort((left, right) => {
      if ((right.updated_time || 0) !== (left.updated_time || 0)) {
        return (right.updated_time || 0) - (left.updated_time || 0);
      }
      return right.id - left.id;
    });
  } finally {
    historyLoading.value = false;
  }
};

const createConversation = async () => {
  const response = await RequestApi('/0x/user/chat-conversations', 'POST', {
    model_name: selectedModel.value,
  });
  if (!response.ok) return null;
  const payload = (await response.json()) as ConversationSummary;
  upsertConversationSummary(payload);
  activeConversationId.value = payload.id;
  await syncRouteToConversation(payload.id);
  return payload;
};

const serializeConversationMessages = () => {
  return messages.value
    .filter((item) => item.role === 'user' || Boolean(item.content.trim()))
    .map((item) => ({
      role: item.role,
      content: item.content,
      account_label: item.accountLabel || '',
    }));
};

const syncActiveConversation = async () => {
  if (!activeConversationId.value) {
    return null;
  }

  const response = await RequestApi(`/0x/user/chat-conversations/${activeConversationId.value}`, 'PUT', {
    model_name: selectedModel.value,
    messages: serializeConversationMessages(),
  });
  if (!response.ok) return null;

  const payload = (await response.json()) as ConversationDetail;
  upsertConversationSummary(payload);
  return payload;
};

const startNewConversation = async (syncRoute = true) => {
  if (pending.value) {
    return;
  }

  activeConversationId.value = null;
  messages.value = [];
  draft.value = '';
  currentEntry.value = null;

  if (syncRoute) {
    await syncRouteToConversation(null);
  }
};

const handleNewConversationClick = async () => {
  await startNewConversation();
};

const openConversation = async (conversationId: number, syncRoute = true) => {
  if (pending.value || conversationLoading.value || activeConversationId.value === conversationId) {
    return;
  }

  conversationLoading.value = true;
  try {
    const response = await RequestApi(`/0x/user/chat-conversations/${conversationId}`);
    if (!response.ok) return;
    const payload = (await response.json()) as ConversationDetail;
    await hydrateConversation(payload);
    if (syncRoute) {
      await syncRouteToConversation(conversationId);
    }
  } finally {
    conversationLoading.value = false;
  }
};

const ensureActiveConversation = async () => {
  if (activeConversationId.value) {
    return activeConversationId.value;
  }
  const conversation = await createConversation();
  return conversation?.id || null;
};

const handleComposerKeydown = async (event: KeyboardEvent) => {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) {
    return;
  }
  event.preventDefault();
  await sendMessage();
};

const applyPrompt = async (prompt: string) => {
  draft.value = prompt;
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

    for (const rawLine of lines) {
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
  if (!content || pending.value || !sessionSummary.value.available || conversationLoading.value) {
    return;
  }

  const conversationId = await ensureActiveConversation();
  if (!conversationId) {
    return;
  }

  const userMessage: ChatMessage = {
    id: createMessageId('user'),
    role: 'user',
    content,
  };
  messages.value.push(userMessage);
  draft.value = '';
  await syncActiveConversation();

  const requestMessages = messages.value
    .filter((item) => item.role === 'user' || (item.role === 'assistant' && item.content.trim()))
    .map((item) => ({
      role: item.role,
      content: item.content,
    }));

  pending.value = true;

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
    await syncActiveConversation();
    await scrollToBottom();
  }
};

const handleRouteState = async () => {
  const routeConversationId = normalizeConversationQueryId(route.query.conversation);
  if (routeConversationId) {
    const currentConversation = conversations.value.find((item) => item.id === routeConversationId);
    if (!currentConversation && conversations.value.length) {
      await syncRouteToConversation(conversations.value[0].id);
      return;
    }
    if (activeConversationId.value !== routeConversationId) {
      await openConversation(routeConversationId, false);
    }
    return;
  }

  const routeNewValue = String(route.query.new || '');
  if (routeNewValue && routeNewValue !== lastHandledNewQuery.value) {
    lastHandledNewQuery.value = routeNewValue;
    await startNewConversation(false);
  }
};

watch(selectedModel, async (nextModel, previousModel) => {
  if (!nextModel || nextModel === previousModel) {
    return;
  }

  modelOptions.value = uniqModelOptions([nextModel, ...modelOptions.value, ...defaultConsumerModels]);
  await refreshChatEntry();

  if (activeConversationId.value && !pending.value) {
    await syncActiveConversation();
  }
});

watch(
  () => [route.query.conversation, route.query.new],
  async () => {
    await handleRouteState();
  }
);

onMounted(async () => {
  const pendingCompose = consumeConsumerComposeState();
  await loadSessionSummary(pendingCompose?.model || '');
  await refreshChatEntry();
  await loadConversationList();

  if (pendingCompose?.prompt && sessionSummary.value.available) {
    await startNewConversation(false);
    draft.value = pendingCompose.prompt;
    await sendMessage();
    return;
  }

  const routeConversationId = normalizeConversationQueryId(route.query.conversation);
  if (routeConversationId) {
    await openConversation(routeConversationId, false);
    return;
  }

  const routeNewValue = String(route.query.new || '');
  if (routeNewValue) {
    lastHandledNewQuery.value = routeNewValue;
    return;
  }

  if (conversations.value.length) {
    await openConversation(conversations.value[0].id);
  }
});
</script>

<style scoped lang="less">
.consumer-chat {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
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

.chat-toolbar-kicker {
  margin: 0;
  color: #7f7466;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.chat-toolbar-title {
  margin: 0;
  color: #16120d;
  font-size: clamp(24px, 3vw, 34px);
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.04em;
}

.chat-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-status-pill {
  padding: 10px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
}

.chat-status-pill.info {
  background: rgba(202, 186, 167, 0.2);
  color: #6d5b49;
}

.chat-status-pill.warn {
  background: rgba(184, 81, 49, 0.12);
  color: #934326;
}

.control-button,
.history-create,
.ghost-action,
.send-action {
  appearance: none;
  border: 0;
  cursor: pointer;
  transition: transform 0.2s ease, opacity 0.2s ease, background 0.2s ease, color 0.2s ease;
}

.control-button,
.history-create {
  padding: 11px 16px;
  border-radius: 999px;
  background: #1d1a17;
  color: #fffdf8;
  font-size: 13px;
  font-weight: 700;
}

.chat-workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
}

.history-panel,
.chat-stage,
.composer-surface {
  border: 1px solid rgba(35, 26, 16, 0.08);
  background: rgba(255, 252, 245, 0.9);
  box-shadow: 0 24px 60px rgba(55, 42, 27, 0.08);
}

.history-panel {
  display: flex;
  min-height: 0;
  flex-direction: column;
  border-radius: 28px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(255, 250, 241, 0.96), rgba(249, 242, 232, 0.92)),
    #fff8ee;
}

.history-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.history-eyebrow {
  margin: 0 0 4px;
  color: #9d8f7c;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.history-title {
  margin: 0;
  color: #1b1712;
  font-size: 18px;
  font-weight: 700;
}

.history-list {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}

.history-item {
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(58, 44, 26, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  color: #201a13;
  text-align: left;
  cursor: pointer;
}

.history-item.active {
  border-color: rgba(56, 121, 85, 0.22);
  background: rgba(232, 243, 235, 0.84);
}

.history-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-item-head strong {
  min-width: 0;
  font-size: 14px;
  line-height: 1.4;
}

.history-item-head span {
  flex-shrink: 0;
  color: #8f806d;
  font-size: 11px;
}

.history-item-preview,
.history-empty {
  margin: 8px 0 0;
  color: #756754;
  font-size: 12px;
  line-height: 1.6;
}

.chat-main {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 14px;
  min-height: 0;
}

.chat-stage {
  min-height: 0;
  border-radius: 30px;
  padding: 22px;
  overflow: hidden;
}

.chat-empty {
  display: flex;
  height: 100%;
  min-height: 420px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  text-align: center;
}

.chat-empty.loading {
  color: #6f6150;
  font-size: 15px;
  font-weight: 600;
}

.empty-kicker {
  margin: 0;
  color: #7d705e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.empty-title {
  margin: 0;
  color: #17130f;
  font-size: clamp(32px, 4vw, 48px);
  font-weight: 700;
  letter-spacing: -0.05em;
}

.empty-copy {
  max-width: 620px;
  margin: 0;
  color: #6f6150;
  font-size: 15px;
  line-height: 1.7;
}

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 12px;
  width: min(100%, 760px);
}

.prompt-pill {
  display: flex;
  min-height: 120px;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border: 1px solid rgba(44, 33, 22, 0.08);
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(244, 236, 224, 0.78));
  color: #1e1812;
  text-align: left;
  cursor: pointer;
}

.prompt-pill span {
  font-size: 15px;
  font-weight: 700;
}

.prompt-pill small {
  color: #6e604e;
  font-size: 13px;
  line-height: 1.6;
}

.message-viewport {
  display: flex;
  height: 100%;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
  padding-right: 6px;
}

.message-row {
  display: flex;
}

.message-row.user {
  justify-content: flex-end;
}

.message-inner {
  display: flex;
  max-width: min(100%, 880px);
  align-items: flex-start;
  gap: 14px;
}

.message-row.user .message-inner {
  flex-direction: row-reverse;
}

.message-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 16px;
  background: #171411;
  color: #fffaf1;
  font-size: 12px;
  font-weight: 800;
}

.message-row.user .message-avatar {
  background: #4f7f64;
}

.message-body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 8px;
}

.message-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #7f725f;
  font-size: 12px;
  font-weight: 600;
}

.message-bubble {
  border-radius: 24px;
  padding: 16px 18px;
  background: #fffaf2;
}

.message-row.user .message-bubble {
  background: #ecf5ef;
}

.message-bubble.pending {
  opacity: 0.86;
}

.message-content {
  margin: 0;
  color: #1a1612;
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.composer-shell {
  padding-bottom: 6px;
}

.composer-surface {
  border-radius: 28px;
  padding: 16px;
}

.composer-surface.disabled {
  opacity: 0.72;
}

.composer-input {
  width: 100%;
  min-height: 104px;
  resize: none;
  border: 0;
  background: transparent;
  color: #17130f;
  font-size: 16px;
  line-height: 1.8;
  outline: none;
}

.composer-input::placeholder {
  color: #958876;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 14px;
}

.composer-meta {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: 10px;
}

.composer-select-shell,
.composer-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(230, 220, 205, 0.42);
  color: #5f5243;
  font-size: 12px;
  font-weight: 700;
}

.composer-select {
  border: 0;
  background: transparent;
  color: #1d1914;
  font-weight: 700;
  outline: none;
}

.composer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ghost-action {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 999px;
  background: rgba(195, 82, 52, 0.12);
  color: #9b4628;
  font-size: 13px;
  font-weight: 700;
}

.send-action {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  background: #1a1714;
  color: #fffaf2;
  font-size: 13px;
  font-weight: 700;
}

.control-button:disabled,
.history-create:disabled,
.ghost-action:disabled,
.send-action:disabled,
.history-item:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.control-button:not(:disabled):hover,
.history-create:not(:disabled):hover,
.ghost-action:not(:disabled):hover,
.send-action:not(:disabled):hover {
  transform: translateY(-1px);
}

@media (max-width: 1180px) {
  .chat-workspace {
    grid-template-columns: 1fr;
  }

  .history-panel {
    max-height: 280px;
  }
}

@media (max-width: 820px) {
  .chat-toolbar,
  .composer-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .chat-stage,
  .history-panel,
  .composer-surface {
    border-radius: 24px;
  }

  .message-inner {
    max-width: 100%;
  }

  .prompt-grid {
    grid-template-columns: 1fr;
  }
}
</style>
