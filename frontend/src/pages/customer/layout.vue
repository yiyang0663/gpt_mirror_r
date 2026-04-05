<template>
  <div class="customer-shell">
    <aside class="customer-rail">
      <div class="customer-rail-main">
        <div class="customer-brand">
          <div class="brand-mark">
            <component :is="LogoOpenai" class="brand-logo" />
          </div>
          <div>
            <p class="brand-eyebrow">ChatGPT Mirror</p>
            <h1 class="brand-title">你的 AI 工作区</h1>
          </div>
        </div>

        <button class="primary-action" type="button" @click="openChat">新聊天</button>

        <div class="rail-section">
          <p class="rail-caption">Workspace</p>

          <nav class="customer-nav">
            <button
              v-for="item in navItems"
              :key="item.name"
              class="customer-nav-link"
              :class="{ active: route.name === item.name }"
              type="button"
              @click="router.push({ name: item.name })"
            >
              <span class="nav-icon" v-html="item.icon"></span>
              <span>{{ item.label }}</span>
            </button>
          </nav>
        </div>

        <div class="rail-note">
          <p class="rail-note-title">统一账号池已接入</p>
          <p class="rail-note-copy">用户登录后直接调用后台配置好的官方账号和中转账号，无需再次填写 Token。</p>
        </div>
      </div>

      <div class="customer-rail-footer">
        <div class="account-chip">
          <span class="account-avatar">{{ userInitial }}</span>
          <div class="account-meta">
            <strong>{{ displayName }}</strong>
            <span>{{ isChatRoute ? 'Chat Workspace' : pageMeta.kicker }}</span>
          </div>
        </div>

        <button class="secondary-action" type="button" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <main class="customer-main" :class="{ 'chat-mode': isChatRoute }">
      <header v-if="!isChatRoute" class="customer-topbar">
        <div>
          <p class="topbar-kicker">{{ pageMeta.kicker }}</p>
          <h2 class="topbar-title">{{ pageMeta.title }}</h2>
        </div>

        <button class="chat-launch" type="button" @click="openChat">
          新对话
          <span class="chat-arrow">↗</span>
        </button>
      </header>

      <section class="customer-stage">
        <router-view />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import LogoOpenai from '@/assets/openai-logo.svg';
import { useUserStore } from '@/store';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const isChatRoute = computed(() => route.name === 'CustomerChat');
const displayName = computed(() => userStore.userInfo.name || 'Chat 用户');
const userInitial = computed(() => displayName.value.trim().charAt(0).toUpperCase() || 'U');

const navItems = [
  {
    name: 'CustomerChat',
    label: '对话',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v7A2.5 2.5 0 0 1 16.5 16H11l-4.2 3.5c-.8.6-1.8 0-1.8-1V16.2A2.5 2.5 0 0 1 4 14V6.5Z"></path></svg>',
  },
  {
    name: 'CustomerHome',
    label: '总览',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11.5 12 4l9 7.5"></path><path d="M5 10.5V20h14v-9.5"></path></svg>',
  },
  {
    name: 'CustomerAccount',
    label: '账户',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.2"></circle><path d="M5 19a7 7 0 0 1 14 0"></path></svg>',
  },
];

const openChat = async () => {
  await router.push({ name: 'CustomerChat' });
};

const pageMeta = computed(() => {
  if (route.name === 'CustomerAccount') {
    return {
      kicker: 'Account',
      title: '账户与套餐',
    };
  }
  if (route.name === 'CustomerHome') {
    return {
      kicker: 'Overview',
      title: '接入总览',
    };
  }
  return {
    kicker: 'Workspace',
    title: '直接开始对话',
  };
});

const handleLogout = async () => {
  await userStore.logout();
  router.push({ name: 'login' });
};
</script>

<style scoped lang="less">
.customer-shell {
  display: flex;
  min-height: 100vh;
  background: #f5f5f2;
  color: #181818;
}

.customer-rail {
  display: flex;
  flex: 0 0 284px;
  flex-direction: column;
  justify-content: space-between;
  gap: 22px;
  padding: 18px 16px;
  background:
    linear-gradient(180deg, rgba(24, 24, 24, 0.98) 0%, rgba(15, 15, 15, 0.98) 100%),
    #121212;
  color: #f3f3ef;
}

.customer-rail-main {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.customer-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.1);
  color: #fffef8;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.brand-logo {
  width: 24px;
  height: 24px;
}

.brand-eyebrow {
  margin: 0 0 4px;
  color: rgba(244, 244, 239, 0.54);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.rail-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rail-caption {
  margin: 0;
  color: rgba(244, 244, 239, 0.44);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.customer-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.customer-nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: rgba(244, 244, 239, 0.76);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.customer-nav-link:hover,
.customer-nav-link.active {
  border-color: rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.08);
  color: #fffef8;
}

.nav-icon {
  width: 18px;
  height: 18px;
  color: currentColor;
}

.nav-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.rail-note {
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
}

.rail-note-title {
  margin: 0 0 8px;
  color: #fffef8;
  font-size: 14px;
  font-weight: 700;
}

.rail-note-copy {
  margin: 0;
  color: rgba(244, 244, 239, 0.68);
  font-size: 13px;
  line-height: 1.7;
}

.customer-rail-footer {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.account-chip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.05);
}

.account-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.12);
  color: #fffef8;
  font-size: 14px;
  font-weight: 700;
}

.account-meta {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.account-meta strong {
  color: #fffef8;
  font-size: 14px;
  font-weight: 700;
}

.account-meta span {
  color: rgba(244, 244, 239, 0.52);
  font-size: 12px;
}

.primary-action,
.secondary-action,
.chat-launch {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.primary-action,
.chat-launch {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: #f3f3ef;
  color: #111;
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.18);
}

.secondary-action {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: #f3f3ef;
}

.primary-action:hover,
.secondary-action:hover,
.chat-launch:hover {
  transform: translateY(-1px);
}

.customer-main {
  flex: 1;
  min-width: 0;
  padding: 18px 22px;
}

.customer-main.chat-mode {
  padding-right: 18px;
}

.customer-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 6px 20px;
}

.topbar-kicker {
  margin: 0 0 6px;
  color: #80807b;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.topbar-title {
  margin: 0;
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 700;
  line-height: 1.02;
  letter-spacing: -0.04em;
}

.chat-arrow {
  margin-left: 10px;
  font-size: 15px;
}

.customer-stage {
  min-width: 0;
  min-height: calc(100vh - 36px);
}

@media (max-width: 960px) {
  .customer-shell {
    flex-direction: column;
  }

  .customer-rail {
    flex: none;
    gap: 18px;
  }

  .customer-nav {
    flex-direction: row;
    overflow-x: auto;
  }

  .customer-rail-footer {
    flex-direction: row;
    align-items: center;
  }

  .customer-topbar {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .customer-main {
    padding: 14px;
  }

  .customer-main.chat-mode {
    padding-right: 14px;
  }

  .customer-rail {
    padding: 14px;
  }

  .customer-nav {
    flex-direction: column;
  }

  .customer-rail-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .chat-launch,
  .primary-action,
  .secondary-action,
  .account-chip {
    width: 100%;
  }
}
</style>
