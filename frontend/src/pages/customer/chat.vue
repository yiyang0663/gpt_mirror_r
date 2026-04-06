<template>
  <div class="consumer-chat">
    <header class="workspace-head">
      <label class="model-switch">
        <span class="model-switch-brand">ChatGPT</span>
        <select v-model="selectedModel" class="model-switch-select" :disabled="pending || conversationLoading">
          <option v-for="item in modelOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <p v-if="!sessionSummary.available" class="workspace-status">{{ statusMessage }}</p>
    </header>

    <div v-if="conversationLoading" class="workspace-loading">正在载入这段对话…</div>

    <div v-else-if="!messages.length" class="workspace-empty">
      <div class="empty-copy">
        <p class="empty-kicker">ChatGPT</p>
        <h1 class="empty-title">有什么可以帮忙的？</h1>
        <p class="empty-note">登录后直接使用站点已配置的账号池，无需再填写任何 Token。</p>
      </div>

      <section class="composer-panel composer-panel-empty">
        <div class="composer-frame">
          <button class="composer-utility" type="button" disabled aria-label="附件能力稍后开放">
            <span v-html="uiIcons.plus"></span>
          </button>

          <textarea
            ref="composerInputRef"
            v-model="draft"
            class="composer-input"
            rows="1"
            placeholder="询问任何问题"
            :disabled="!sessionSummary.available || pending || conversationLoading"
            @input="handleDraftInput"
            @keydown="handleComposerKeydown"
          ></textarea>

          <button class="send-button" type="button" :disabled="!canSend" @click="sendMessage">
            <span v-html="pending ? uiIcons.stop : uiIcons.arrowUp"></span>
          </button>
        </div>

        <div class="composer-meta">
          <p class="composer-disclaimer" :class="{ warning: !sessionSummary.available }">{{ composerDisclaimer }}</p>
          <button v-if="pending" class="stop-button" type="button" @click="stopGeneration">停止生成</button>
        </div>
      </section>

      <div class="starter-grid">
        <button v-for="item in promptIdeas" :key="item.label" class="starter-card" type="button" @click="applyPrompt(item.prompt)">
          <strong>{{ item.label }}</strong>
          <span>{{ item.prompt }}</span>
        </button>
      </div>
    </div>

    <div v-else class="workspace-thread">
      <div ref="messageViewportRef" class="thread-viewport">
        <article
          v-for="item in messages"
          :key="item.id"
          class="message-block"
          :class="item.role === 'user' ? 'user' : 'assistant'"
        >
          <div v-if="item.role !== 'user'" class="assistant-mark">
            <component :is="LogoOpenai" class="assistant-logo" />
          </div>

          <div class="message-stack">
            <div class="message-head">
              <span>{{ item.role === 'user' ? '你' : 'ChatGPT' }}</span>
            </div>

            <div class="message-body" :class="{ pending: item.pending, bubble: item.role === 'user' }">
              <div
                v-if="item.role === 'assistant'"
                class="message-rich"
                v-html="renderAssistantMessage(item.content || (item.pending ? '正在生成回复…' : '暂无内容'))"
              ></div>
              <p v-else class="message-content">{{ item.content || (item.pending ? '正在生成回复…' : '暂无内容') }}</p>
            </div>

            <div v-if="!item.pending && item.content.trim()" class="message-actions">
              <button class="message-action" type="button" @click="copyMessage(item.content)">复制</button>
              <button
                v-if="item.role === 'assistant' && canRegenerate(item.id)"
                class="message-action"
                type="button"
                @click="regenerateLastResponse"
              >
                重新生成
              </button>
            </div>
          </div>
        </article>
      </div>

      <footer class="composer-shell">
        <section class="composer-panel">
          <div class="composer-frame">
            <button class="composer-utility" type="button" disabled aria-label="附件能力稍后开放">
              <span v-html="uiIcons.plus"></span>
            </button>

            <textarea
              ref="threadComposerInputRef"
              v-model="draft"
              class="composer-input"
              rows="1"
              placeholder="继续提问"
              :disabled="!sessionSummary.available || pending || conversationLoading"
              @input="handleDraftInput"
              @keydown="handleComposerKeydown"
            ></textarea>

            <button class="send-button" type="button" :disabled="!canSend" @click="sendMessage">
              <span v-html="pending ? uiIcons.stop : uiIcons.arrowUp"></span>
            </button>
          </div>

          <div class="composer-meta">
            <p class="composer-disclaimer" :class="{ warning: !sessionSummary.available }">{{ composerDisclaimer }}</p>
            <button v-if="pending" class="stop-button" type="button" @click="stopGeneration">停止生成</button>
          </div>
        </section>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import LogoOpenai from '@/assets/openai-logo.svg';
import {
  type CustomerConversationDetail,
  type CustomerConversationSummary,
  useCustomerConversations,
} from '@/composables/use-customer-conversations';
import RequestApi from '@/api/request';
import { renderChatMarkdown } from '@/utils/chat-markdown';
import { defaultConsumerModels, getConsumerChatEntry, type ConsumerChatEntry } from '@/utils/direct-chat';

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

const router = useRouter();
const route = useRoute();
const { conversations, activeConversationId, loadConversationList, upsertConversationSummary } = useCustomerConversations();

const uiIcons = {
  plus:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"></path><path d="M5 12h14"></path></svg>',
  arrowUp:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 5 5 5"></path><path d="m12 5-5 5"></path><path d="M12 5v14"></path></svg>',
  stop:
    '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="7" y="7" width="10" height="10" rx="2"></rect></svg>',
};

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
const selectedModel = ref('gpt-5.4');
const draft = ref('');
const pending = ref(false);
const messages = ref<ChatMessage[]>([]);
const currentEntry = ref<ConsumerChatEntry | null>(null);
const messageViewportRef = ref<HTMLElement | null>(null);
const composerInputRef = ref<HTMLTextAreaElement | null>(null);
const threadComposerInputRef = ref<HTMLTextAreaElement | null>(null);
const activeAbortController = ref<AbortController | null>(null);
const conversationLoading = ref(false);
const modelOptions = ref<string[]>([]);
const lastHandledNewQuery = ref('');
const lastHandledPrefill = ref('');

const promptIdeas = [
  {
    label: '写方案',
    prompt: '帮我写一版针对新用户的产品介绍文案',
  },
  {
    label: '拆任务',
    prompt: '把这个需求拆成 P0 / P1 / P2 的开发任务',
  },
  {
    label: '做运营',
    prompt: '帮我生成一版适合朋友圈发布的活动预告',
  },
  {
    label: '解释问题',
    prompt: '用通俗的方式解释这个问题，并给我一个简单例子',
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

const statusMessage = computed(() => {
  return sessionSummary.value.available
    ? sessionSummary.value.web_quota_status.warnings?.[0] || '当前会话已连接站点统一账号池。'
    : sessionSummary.value.reason || sessionSummary.value.web_quota_status.reason || '当前账号暂未开放网页聊天';
});

const composerDisclaimer = computed(() => {
  return sessionSummary.value.available ? 'ChatGPT 可能会犯错，请核查重要信息。' : statusMessage.value;
});

const renderAssistantMessage = (content: string) => {
  return renderChatMarkdown(content);
};

const lastAssistantMessageId = computed(() => {
  const lastMessage = [...messages.value].reverse().find((item) => item.role === 'assistant');
  return lastMessage?.id || '';
});

const canSend = computed(() => {
  return Boolean(draft.value.trim()) && sessionSummary.value.available && !pending.value && !conversationLoading.value;
});

const scrollToBottom = async () => {
  await nextTick();
  if (!messageViewportRef.value) return;
  messageViewportRef.value.scrollTop = messageViewportRef.value.scrollHeight;
};

const resizeTextarea = (element: HTMLTextAreaElement | null) => {
  if (!element) {
    return;
  }

  element.style.height = 'auto';
  element.style.height = `${Math.min(element.scrollHeight, 180)}px`;
};

const syncComposerHeights = async () => {
  await nextTick();
  resizeTextarea(composerInputRef.value);
  resizeTextarea(threadComposerInputRef.value);
};

const focusComposer = async () => {
  await syncComposerHeights();
  composerInputRef.value?.focus();
  threadComposerInputRef.value?.focus();
};

const handleDraftInput = async () => {
  await syncComposerHeights();
};

const normalizeConversationQueryId = (value: unknown) => {
  const rawValue = Array.isArray(value) ? value[0] : value;
  const normalized = Number(rawValue);
  return Number.isInteger(normalized) && normalized > 0 ? normalized : null;
};

const normalizeStringQuery = (value: unknown) => {
  const rawValue = Array.isArray(value) ? value[0] : value;
  return String(rawValue || '').trim();
};

const syncRouteToConversation = async (conversationId: number | null, prefill = '') => {
  const nextQuery = conversationId
    ? { conversation: String(conversationId) }
    : {
        new: String(Date.now()),
        ...(prefill ? { prefill } : {}),
      };
  await router.replace({
    name: 'CustomerChat',
    query: nextQuery,
  });
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

const hydrateConversation = async (payload: CustomerConversationDetail) => {
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

const createConversation = async () => {
  const response = await RequestApi('/0x/user/chat-conversations', 'POST', {
    model_name: selectedModel.value,
  });
  if (!response.ok) return null;
  const payload = (await response.json()) as CustomerConversationSummary;
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

  const payload = (await response.json()) as CustomerConversationDetail;
  upsertConversationSummary(payload);
  return payload;
};

const startNewConversation = async (syncRoute = true, prefill = '') => {
  if (pending.value) {
    return;
  }

  activeConversationId.value = null;
  messages.value = [];
  draft.value = prefill;
  currentEntry.value = null;

  if (syncRoute) {
    await syncRouteToConversation(null, prefill);
  }
  await focusComposer();
};

const openConversation = async (conversationId: number, syncRoute = true) => {
  if (pending.value || conversationLoading.value || activeConversationId.value === conversationId) {
    return;
  }

  conversationLoading.value = true;
  try {
    const response = await RequestApi(`/0x/user/chat-conversations/${conversationId}`);
    if (!response.ok) return;
    const payload = (await response.json()) as CustomerConversationDetail;
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

const canRegenerate = (messageId: string) => {
  return !pending.value && lastAssistantMessageId.value === messageId && sessionSummary.value.available;
};

const copyMessage = async (content: string) => {
  try {
    await navigator.clipboard.writeText(content);
    MessagePlugin.success('已复制');
  } catch (error) {
    console.error(error);
    MessagePlugin.error('复制失败');
  }
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

const buildRequestMessages = () => {
  return messages.value
    .filter((item) => item.role === 'user' || (item.role === 'assistant' && item.content.trim()))
    .map((item) => ({
      role: item.role,
      content: item.content,
    }));
};

const requestAssistantReply = async (requestMessages: Array<{ role: string; content: string }>) => {
  if (!requestMessages.length) {
    return;
  }

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
  await syncComposerHeights();
  await syncActiveConversation();
  await requestAssistantReply(buildRequestMessages());
};

const regenerateLastResponse = async () => {
  if (pending.value || conversationLoading.value || !sessionSummary.value.available) {
    return;
  }

  const lastMessage = messages.value[messages.value.length - 1];
  if (!lastMessage || lastMessage.role !== 'assistant') {
    return;
  }

  messages.value = messages.value.slice(0, -1);
  await syncActiveConversation();
  await requestAssistantReply(buildRequestMessages());
};

const applyPrefill = async (prefill: string) => {
  if (!prefill) {
    return;
  }
  draft.value = prefill;
  lastHandledPrefill.value = prefill;
  await focusComposer();
};

const handleRouteState = async () => {
  const routeConversationId = normalizeConversationQueryId(route.query.conversation);
  const routeNewValue = normalizeStringQuery(route.query.new);
  const routePrefill = normalizeStringQuery(route.query.prefill);

  if (routeConversationId) {
    if (activeConversationId.value !== routeConversationId) {
      await openConversation(routeConversationId, false);
    }
    return;
  }

  if (routeNewValue && routeNewValue !== lastHandledNewQuery.value) {
    lastHandledNewQuery.value = routeNewValue;
    await startNewConversation(false, routePrefill);
    if (routePrefill) {
      await applyPrefill(routePrefill);
    }
    return;
  }

  if (routePrefill && routePrefill !== lastHandledPrefill.value) {
    await startNewConversation(false, routePrefill);
    await applyPrefill(routePrefill);
    return;
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

watch(draft, async () => {
  await syncComposerHeights();
});

watch(
  () => [route.query.conversation, route.query.new, route.query.prefill],
  async () => {
    await handleRouteState();
  }
);

onMounted(async () => {
  await loadSessionSummary(normalizeStringQuery(route.query.model));
  await refreshChatEntry();
  if (!conversations.value.length) {
    await loadConversationList();
  }
  await handleRouteState();
  await focusComposer();
});
</script>

<style scoped lang="less">
.consumer-chat {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  min-height: 100vh;
  background: #ffffff;
}

.workspace-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 28px 10px;
  border-bottom: 1px solid rgba(17, 17, 17, 0.05);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(18px);
}

.model-switch {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid rgba(17, 17, 17, 0.06);
  border-radius: 999px;
  background: rgba(17, 17, 17, 0.03);
}

.model-switch-brand {
  font-size: 14px;
  font-weight: 700;
}

.model-switch-select {
  min-width: 140px;
  border: 0;
  background: transparent;
  color: #6b6b66;
  font-size: 13px;
  font-weight: 600;
  outline: none;
}

.workspace-status {
  margin: 0;
  color: #93652f;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.5;
  text-align: right;
}

.workspace-loading,
.workspace-empty,
.workspace-thread {
  min-height: 0;
}

.workspace-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6e6e67;
  font-size: 15px;
  font-weight: 600;
}

.workspace-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 48px 28px 64px;
}

.empty-copy {
  display: flex;
  max-width: 540px;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.empty-kicker {
  margin: 0;
  color: #9b9b93;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.empty-title {
  margin: 0;
  color: #171717;
  font-size: clamp(34px, 4.8vw, 48px);
  font-weight: 700;
  letter-spacing: -0.05em;
  text-align: center;
}

.empty-note {
  margin: 0;
  color: #86867e;
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
}

.composer-panel {
  width: min(100%, 780px);
  padding: 12px 14px 10px;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 28px;
  background: #ffffff;
  box-shadow: 0 18px 48px rgba(17, 17, 17, 0.06);
}

.composer-panel-empty {
  margin-top: -4px;
}

.composer-frame {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: end;
  gap: 10px;
}

.composer-utility,
.send-button,
.stop-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  cursor: pointer;
}

.composer-utility {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: #f4f4f2;
  color: #76766f;
  cursor: default;
}

.composer-utility span,
.send-button span {
  width: 18px;
  height: 18px;
}

.composer-utility span :deep(svg),
.send-button span :deep(svg) {
  width: 18px;
  height: 18px;
}

.composer-input {
  width: 100%;
  min-height: 28px;
  max-height: 180px;
  padding: 8px 0 6px;
  resize: none;
  border: 0;
  background: transparent;
  color: #171717;
  font-size: 16px;
  line-height: 1.75;
  outline: none;
}

.composer-input::placeholder {
  color: #8a8a83;
}

.send-button {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: #171717;
  color: #ffffff;
}

.send-button:disabled {
  background: #d7d7d2;
  color: #92928a;
  cursor: not-allowed;
}

.composer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}

.composer-disclaimer {
  margin: 0;
  color: #83837b;
  font-size: 12px;
  line-height: 1.6;
}

.composer-disclaimer.warning {
  color: #93652f;
}

.stop-button {
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(199, 81, 51, 0.12);
  color: #a64527;
  font-size: 12px;
  font-weight: 700;
}

.starter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: min(100%, 780px);
}

.starter-card {
  display: flex;
  min-height: 82px;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 14px 16px;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 18px;
  background: #f7f7f5;
  color: #1a1a19;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.starter-card:hover {
  background: #f0f0ed;
  transform: translateY(-1px);
}

.starter-card strong {
  font-size: 14px;
  font-weight: 700;
}

.starter-card span {
  color: #73736d;
  font-size: 12px;
  line-height: 1.55;
}

.workspace-thread {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-height: 0;
}

.thread-viewport {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 34px;
  overflow-y: auto;
  padding: 24px 28px 18px;
}

.message-block {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 14px;
  width: min(100%, 820px);
  margin: 0 auto;
}

.message-block.user {
  grid-template-columns: minmax(0, 1fr);
}

.assistant-mark {
  display: inline-flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 2px;
}

.assistant-logo {
  width: 18px;
  height: 18px;
  color: #191919;
}

.message-stack {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6px;
}

.message-block.user .message-stack {
  align-items: flex-end;
}

.message-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #77776f;
  font-size: 12px;
  font-weight: 600;
}

.message-block.user .message-head {
  justify-content: flex-end;
}

.message-body {
  width: 100%;
  color: #191919;
}

.message-body.bubble {
  width: auto;
  max-width: min(72%, 680px);
  padding: 14px 18px;
  border-radius: 26px;
  background: #f1f1ee;
}

.message-body.pending {
  opacity: 0.76;
}

.message-content {
  margin: 0;
  font-size: 15px;
  line-height: 1.85;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-rich {
  font-size: 15px;
  line-height: 1.85;
  word-break: break-word;
}

.message-rich :deep(*) {
  box-sizing: border-box;
}

.message-rich :deep(p),
.message-rich :deep(ul),
.message-rich :deep(ol),
.message-rich :deep(blockquote),
.message-rich :deep(pre),
.message-rich :deep(h1),
.message-rich :deep(h2),
.message-rich :deep(h3) {
  margin: 0 0 14px;
}

.message-rich :deep(p:last-child),
.message-rich :deep(ul:last-child),
.message-rich :deep(ol:last-child),
.message-rich :deep(blockquote:last-child),
.message-rich :deep(pre:last-child),
.message-rich :deep(h1:last-child),
.message-rich :deep(h2:last-child),
.message-rich :deep(h3:last-child) {
  margin-bottom: 0;
}

.message-rich :deep(h1),
.message-rich :deep(h2),
.message-rich :deep(h3) {
  color: #141414;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.message-rich :deep(h1) {
  font-size: 24px;
}

.message-rich :deep(h2) {
  font-size: 20px;
}

.message-rich :deep(h3) {
  font-size: 17px;
}

.message-rich :deep(ul),
.message-rich :deep(ol) {
  padding-left: 22px;
}

.message-rich :deep(li + li) {
  margin-top: 6px;
}

.message-rich :deep(blockquote) {
  padding-left: 14px;
  border-left: 3px solid rgba(17, 17, 17, 0.14);
  color: #5f5f58;
}

.message-rich :deep(code) {
  padding: 0.18em 0.45em;
  border-radius: 8px;
  background: #f3f3f1;
  font-family: 'SFMono-Regular', 'SF Mono', Menlo, Monaco, Consolas, monospace;
  font-size: 0.92em;
}

.message-rich :deep(.chat-code-block) {
  overflow: hidden;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 18px;
  background: #1f1f1d;
  color: #f5f5f3;
}

.message-rich :deep(.chat-code-head) {
  display: flex;
  align-items: center;
  min-height: 38px;
  padding: 0 14px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.message-rich :deep(.chat-code-block code) {
  display: block;
  overflow-x: auto;
  padding: 14px;
  background: transparent;
  color: inherit;
  font-size: 13px;
  line-height: 1.75;
}

.message-rich :deep(a) {
  color: #0b6bcb;
  text-decoration: none;
}

.message-rich :deep(a:hover) {
  text-decoration: underline;
}

.message-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.message-block.user .message-actions {
  justify-content: flex-end;
}

.message-action {
  min-height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: 999px;
  background: rgba(17, 17, 17, 0.05);
  color: #65655f;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.message-action:hover {
  background: rgba(17, 17, 17, 0.1);
  color: #1c1c1a;
}

.composer-shell {
  padding: 0 28px 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, #ffffff 32%);
}

@media (max-width: 920px) {
  .workspace-head {
    flex-direction: column;
    align-items: flex-start;
    padding: 14px 18px 12px;
  }

  .workspace-status {
    text-align: left;
  }

  .workspace-empty {
    padding: 36px 18px 54px;
  }

  .thread-viewport {
    padding: 22px 18px 16px;
  }

  .composer-shell {
    padding: 0 18px 18px;
  }

  .starter-grid {
    grid-template-columns: 1fr;
  }

  .message-block {
    width: 100%;
  }

  .message-body.bubble {
    max-width: 88%;
  }
}
</style>
