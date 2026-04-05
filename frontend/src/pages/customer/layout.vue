<template>
  <div class="customer-shell">
    <aside class="customer-rail">
      <div class="customer-brand">
        <div class="brand-mark">
          <component :is="LogoOpenai" class="brand-logo" />
        </div>
        <div>
          <p class="brand-eyebrow">ChatGPT Mirror</p>
          <h1 class="brand-title">用户中心</h1>
        </div>
      </div>

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

      <div class="customer-rail-footer">
        <button class="primary-action" type="button" @click="openChat">开始对话</button>
        <button class="secondary-action" type="button" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <main class="customer-main">
      <header class="customer-topbar">
        <div>
          <p class="topbar-kicker">{{ route.name === 'CustomerAccount' ? 'Account' : 'Workspace' }}</p>
          <h2 class="topbar-title">{{ route.name === 'CustomerAccount' ? '账户与套餐' : '欢迎回来' }}</h2>
        </div>

        <button class="chat-launch" type="button" @click="openChat">
          进入对话
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
import Cookies from 'js-cookie';
import { useRoute, useRouter } from 'vue-router';

import LogoOpenai from '@/assets/openai-logo.svg';
import { useUserStore } from '@/store';
import { redirectToConsumerChat } from '@/utils/direct-chat';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const navItems = [
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
  await redirectToConsumerChat();
};

const handleLogout = async () => {
  await userStore.logout();
  Cookies.remove('user_token');
  router.push({ name: 'login' });
};
</script>

<style scoped lang="less">
.customer-shell {
  display: flex;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(239, 246, 241, 0.96), rgba(248, 245, 239, 0.96) 36%),
    linear-gradient(180deg, #f6f3ec 0%, #f4f6f1 100%);
  color: #17221d;
}

.customer-rail {
  display: flex;
  flex: 0 0 270px;
  flex-direction: column;
  justify-content: space-between;
  padding: 20px 18px;
  border-right: 1px solid rgba(16, 24, 19, 0.08);
  background: rgba(250, 249, 245, 0.7);
  backdrop-filter: blur(18px);
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
  background: #17221d;
  color: #fff;
}

.brand-logo {
  width: 24px;
  height: 24px;
}

.brand-eyebrow {
  margin: 0 0 4px;
  color: #708176;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.05;
}

.customer-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 28px;
}

.customer-nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 16px;
  background: transparent;
  color: #24312a;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.customer-nav-link:hover,
.customer-nav-link.active {
  border-color: rgba(17, 28, 22, 0.08);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 12px 28px rgba(17, 28, 22, 0.06);
}

.nav-icon {
  width: 18px;
  height: 18px;
  color: #5f7165;
}

.nav-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.customer-rail-footer {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.primary-action,
.secondary-action,
.chat-launch {
  min-height: 46px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.primary-action,
.chat-launch {
  border: none;
  background: #17221d;
  color: #fff;
  box-shadow: 0 18px 36px rgba(23, 34, 29, 0.18);
}

.secondary-action {
  border: 1px solid rgba(23, 34, 29, 0.12);
  background: rgba(255, 255, 255, 0.68);
  color: #18251f;
}

.primary-action:hover,
.secondary-action:hover,
.chat-launch:hover {
  transform: translateY(-1px);
}

.customer-main {
  flex: 1;
  min-width: 0;
  padding: 20px;
}

.customer-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 2px 18px;
}

.topbar-kicker {
  margin: 0 0 6px;
  color: #738176;
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
}

.chat-arrow {
  margin-left: 10px;
  font-size: 15px;
}

.customer-stage {
  min-width: 0;
}

@media (max-width: 960px) {
  .customer-shell {
    flex-direction: column;
  }

  .customer-rail {
    flex: none;
    gap: 18px;
    border-right: none;
    border-bottom: 1px solid rgba(16, 24, 19, 0.08);
  }

  .customer-nav {
    flex-direction: row;
    margin-top: 0;
  }

  .customer-rail-footer {
    flex-direction: row;
  }

  .customer-topbar {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .customer-main {
    padding: 16px;
  }

  .customer-nav {
    flex-direction: column;
  }

  .customer-rail-footer {
    flex-direction: column;
  }

  .chat-launch,
  .primary-action,
  .secondary-action {
    width: 100%;
  }
}
</style>
