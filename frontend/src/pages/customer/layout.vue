<template>
  <div class="customer-shell">
    <aside class="customer-sidebar">
      <div class="sidebar-top">
        <div class="brand-row">
          <button class="brand-button" type="button" @click="openChat">
            <span class="brand-mark">
              <component :is="LogoOpenai" class="brand-logo" />
            </span>
            <strong class="brand-name">ChatGPT</strong>
          </button>
        </div>

        <button class="sidebar-action sidebar-action-primary" type="button" @click="openChat">
          <span class="action-copy">
            <span class="action-title">新聊天</span>
            <span class="action-meta">⌘ O</span>
          </span>
          <span class="action-icon" v-html="icons.compose"></span>
        </button>

        <button class="sidebar-action" type="button" @click="toggleHistorySearch">
          <span class="action-copy">
            <span class="action-title">搜索聊天</span>
            <span class="action-meta">⌘ K</span>
          </span>
          <span class="action-icon" v-html="icons.search"></span>
        </button>

        <section class="history-shell">
          <div class="history-shell-head">
            <p>历史记录</p>
            <span>{{ filteredConversations.length }}</span>
          </div>

          <div v-if="historySearchOpen || historyQuery" class="history-search-shell">
            <span class="history-search-icon" v-html="icons.search"></span>
            <input
              ref="historyInputRef"
              v-model="historyQuery"
              class="history-search-input"
              type="text"
              placeholder="搜索聊天标题或内容"
            />
          </div>

          <div class="history-list">
            <button
              v-for="item in filteredConversations"
              :key="item.id"
              class="history-link"
              :class="{ active: item.id === activeConversationId }"
              type="button"
              @click="openConversation(item.id)"
            >
              <span class="history-link-title">{{ item.title || '新对话' }}</span>
              <span class="history-link-meta">{{ formatConversationTime(item.updated_time || item.created_time) }}</span>
            </button>

            <p v-if="historyLoading" class="history-empty">正在加载会话…</p>
            <p v-else-if="!filteredConversations.length" class="history-empty">
              {{ historyQuery ? '没有匹配的历史会话。' : '开始第一段对话后，这里会自动出现历史记录。' }}
            </p>
          </div>
        </section>
      </div>

      <div class="sidebar-footer">
        <button class="account-trigger" type="button" @click="router.push({ name: 'CustomerAccount' })">
          <span class="account-avatar">{{ userInitial }}</span>
          <span class="account-copy">
            <strong>{{ displayName }}</strong>
            <span>{{ currentFootnote }}</span>
          </span>
        </button>

        <div class="account-actions">
          <button class="footer-link" type="button" @click="router.push({ name: 'CustomerAccount' })">账户</button>
          <button class="footer-link footer-link-danger" type="button" @click="handleLogout">退出</button>
        </div>
      </div>
    </aside>

    <main class="customer-main" :class="{ 'chat-main': isChatRoute }">
      <header v-if="!isChatRoute" class="customer-topbar">
        <div>
          <p class="topbar-kicker">{{ pageMeta.kicker }}</p>
          <h2 class="topbar-title">{{ pageMeta.title }}</h2>
        </div>

        <button class="topbar-action" type="button" @click="openChat">
          打开聊天
          <span v-html="icons.compose"></span>
        </button>
      </header>

      <section class="customer-stage">
        <router-view />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import LogoOpenai from '@/assets/openai-logo.svg';
import { useCustomerConversations } from '@/composables/use-customer-conversations';
import { useUserStore } from '@/store';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const { conversations, activeConversationId, historyLoading, loadConversationList, resetConversationState } =
  useCustomerConversations();

const historyQuery = ref('');
const historySearchOpen = ref(false);
const historyInputRef = ref<HTMLInputElement | null>(null);

const icons = {
  compose:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4l10-10-4-4L4 16v4Z"></path><path d="m13 7 4 4"></path></svg>',
  search:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="6"></circle><path d="m20 20-3.5-3.5"></path></svg>',
};

const isChatRoute = computed(() => route.name === 'CustomerChat');
const displayName = computed(() => userStore.userInfo.name || 'Chat 用户');
const userInitial = computed(() => displayName.value.trim().charAt(0).toUpperCase() || 'C');
const currentFootnote = computed(() => (isChatRoute.value ? 'Chat Workspace' : pageMeta.value.kicker));

const filteredConversations = computed(() => {
  const keyword = historyQuery.value.trim().toLowerCase();
  if (!keyword) {
    return conversations.value;
  }
  return conversations.value.filter((item) => {
    return [item.title, item.preview_text, item.model_name].some((field) => String(field || '').toLowerCase().includes(keyword));
  });
});

const pageMeta = computed(() => {
  if (route.name === 'CustomerAccount') {
    return {
      kicker: 'Account',
      title: '套餐与使用情况',
    };
  }
  if (route.name === 'CustomerHome') {
    return {
      kicker: 'Overview',
      title: '使用概览',
    };
  }
  return {
    kicker: 'Workspace',
    title: '对话工作台',
  };
});

const formatConversationTime = (timestamp: number) => {
  if (!timestamp) return '刚刚';
  const date = new Date(timestamp * 1000);
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
  }).format(date);
};

const openChat = async () => {
  await router.push({
    name: 'CustomerChat',
    query: {
      new: String(Date.now()),
    },
  });
};

const openConversation = async (conversationId: number) => {
  await router.push({
    name: 'CustomerChat',
    query: {
      conversation: String(conversationId),
    },
  });
};

const toggleHistorySearch = async () => {
  historySearchOpen.value = !historySearchOpen.value;
  if (historySearchOpen.value) {
    await nextTick();
    historyInputRef.value?.focus();
  } else {
    historyQuery.value = '';
  }
};

const handleLogout = async () => {
  resetConversationState();
  await userStore.logout();
  router.push({ name: 'login' });
};

watch(
  () => route.name,
  async (nextRoute) => {
    if (nextRoute === 'CustomerChat' && userStore.token && !conversations.value.length) {
      await loadConversationList();
    }
  },
  { immediate: true }
);

onMounted(async () => {
  if (userStore.token && !conversations.value.length) {
    await loadConversationList();
  }
});
</script>

<style scoped lang="less">
:root {
  --chat-shell-bg: #ffffff;
  --chat-sidebar-bg: #f8f8f7;
  --chat-sidebar-border: rgba(23, 23, 23, 0.08);
  --chat-sidebar-text: #202020;
  --chat-muted: #7d7d76;
  --chat-subtle: #a1a19a;
  --chat-hover: rgba(17, 17, 17, 0.05);
  --chat-active: #ecece8;
  --chat-main-bg: #ffffff;
  --chat-line: rgba(17, 17, 17, 0.08);
  --chat-strong: #111111;
}

.customer-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 100vh;
  background: var(--chat-shell-bg);
  color: var(--chat-strong);
}

.customer-sidebar {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  justify-content: space-between;
  border-right: 1px solid var(--chat-sidebar-border);
  background: var(--chat-sidebar-bg);
  padding: 14px 12px 12px;
}

.sidebar-top {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 10px;
}

.brand-row {
  padding: 2px 4px 10px;
}

.brand-button {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 6px;
  border: 0;
  background: transparent;
  color: var(--chat-strong);
  cursor: pointer;
  text-align: left;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(17, 17, 17, 0.08);
}

.brand-logo {
  width: 16px;
  height: 16px;
}

.brand-name {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.sidebar-action,
.footer-link,
.account-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 42px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: var(--chat-sidebar-text);
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.sidebar-action {
  padding: 0 12px;
}

.sidebar-action:hover,
.footer-link:hover,
.history-link:hover,
.account-trigger:hover,
.brand-button:hover {
  background: var(--chat-hover);
}

.sidebar-action-primary {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(17, 17, 17, 0.08);
}

.action-copy {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.action-title {
  font-size: 14px;
  font-weight: 600;
}

.action-meta {
  color: var(--chat-subtle);
  font-size: 11px;
  font-weight: 600;
}

.action-icon {
  width: 17px;
  height: 17px;
  color: currentColor;
}

.action-icon :deep(svg) {
  width: 17px;
  height: 17px;
}

.history-shell {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  padding-top: 10px;
}

.history-shell-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  color: var(--chat-subtle);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.history-shell-head p {
  margin: 0;
}

.history-search-shell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 12px;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(17, 17, 17, 0.08);
}

.history-search-icon {
  width: 14px;
  height: 14px;
  color: var(--chat-subtle);
}

.history-search-icon :deep(svg) {
  width: 14px;
  height: 14px;
}

.history-search-input {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--chat-strong);
  font-size: 13px;
  outline: none;
}

.history-list {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.history-link {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  padding: 10px 12px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: #30302d;
  text-align: left;
  cursor: pointer;
}

.history-link.active {
  background: var(--chat-active);
}

.history-link-title {
  width: 100%;
  overflow: hidden;
  color: #1f1f1d;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-link-meta {
  color: var(--chat-subtle);
  font-size: 11px;
}

.history-empty {
  margin: 0;
  padding: 12px;
  color: var(--chat-muted);
  font-size: 12px;
  line-height: 1.6;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
}

.account-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 0;
  border-radius: 16px;
  background: #ffffff;
  color: #1d1d1b;
  cursor: pointer;
  text-align: left;
  box-shadow: inset 0 0 0 1px rgba(17, 17, 17, 0.08);
}

.account-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: #2b2b29;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
}

.account-copy {
  display: inline-flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.account-copy strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-copy span {
  color: var(--chat-muted);
  font-size: 12px;
}

.account-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.footer-link {
  justify-content: center;
  min-height: 38px;
  border: 0;
  border-radius: 12px;
  background: rgba(17, 17, 17, 0.04);
  color: #353532;
  font-size: 13px;
  font-weight: 600;
}

.footer-link-danger {
  color: #8f3b23;
  background: rgba(201, 87, 56, 0.1);
}

.customer-main {
  display: flex;
  min-width: 0;
  min-height: 100vh;
  flex-direction: column;
  background: var(--chat-main-bg);
}

.customer-main.chat-main {
  overflow: hidden;
}

.customer-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 28px 36px 16px;
}

.topbar-kicker {
  margin: 0 0 6px;
  color: var(--chat-subtle);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.topbar-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.04em;
}

.topbar-action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid var(--chat-line);
  border-radius: 999px;
  background: #ffffff;
  color: #181818;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.topbar-action span:last-child {
  width: 16px;
  height: 16px;
}

.topbar-action span:last-child :deep(svg) {
  width: 16px;
  height: 16px;
}

.customer-stage {
  min-height: 0;
  flex: 1;
}

@media (max-width: 1040px) {
  .customer-shell {
    grid-template-columns: 1fr;
  }

  .customer-sidebar {
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--chat-sidebar-border);
  }

  .history-shell {
    max-height: 240px;
  }
}

@media (max-width: 720px) {
  .customer-topbar {
    flex-direction: column;
    align-items: flex-start;
    padding: 20px 18px 12px;
  }

  .customer-sidebar {
    padding: 12px 10px;
  }
}
</style>
