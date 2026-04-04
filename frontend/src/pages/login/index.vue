<template>
  <div class="entry-shell">
    <aside class="entry-sidebar">
      <div class="sidebar-header">
        <div class="brand-mark">
          <component :is="LogoOpenai" class="brand-logo" />
        </div>
        <button class="ghost-icon" type="button" @click="openPanel('login')" aria-label="打开登录">
          <span class="icon-wrap" v-html="getIcon('panel')"></span>
        </button>
      </div>

      <nav class="sidebar-nav">
        <button
          v-for="item in primaryNav"
          :key="item.label"
          class="nav-link"
          type="button"
          @click="openPanel('login')"
        >
          <span class="icon-wrap nav-icon" v-html="getIcon(item.icon)"></span>
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.shortcut" class="nav-shortcut">{{ item.shortcut }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <button
          v-for="item in secondaryNav"
          :key="item.label"
          class="nav-link nav-link-secondary"
          type="button"
          @click="openPanel('login')"
        >
          <span class="icon-wrap nav-icon" v-html="getIcon(item.icon)"></span>
          <span class="nav-label">{{ item.label }}</span>
        </button>

        <div class="signin-card">
          <p class="signin-title">获取为你量身定制的回复</p>
          <p class="signin-copy">登录以获取基于已保存聊天的回答，并可创建图片和上传文件。</p>

          <button class="signin-button" type="button" @click="openPanel('login')">登录</button>
          <button class="signin-link" type="button" @click="goFree">免费体验</button>

          <div v-if="cfg.notice" class="notice-copy" v-html="cfg.notice"></div>

          <a
            v-if="cfg.show_github"
            class="github-link"
            href="https://github.com/dairoot/ChatGPT-Mirror"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </div>
      </div>
    </aside>

    <main class="entry-main">
      <div class="topbar">
        <button class="model-switch" type="button" @click="openPanel('login')">
          ChatGPT
          <span class="icon-wrap tiny-icon" v-html="getIcon('chevron')"></span>
        </button>

        <div class="topbar-actions">
          <button class="topbar-login" type="button" @click="openPanel('login')">登录</button>
          <button class="topbar-register" type="button" @click="openPanel('register')">免费注册</button>
        </div>
      </div>

      <section class="hero">
        <h1 class="hero-title">你今天在想些什么？</h1>

        <button class="prompt-bar" type="button" @click="openPanel('login')">
          <span class="prompt-leading icon-wrap" v-html="getIcon('plus')"></span>
          <span class="prompt-text">有问题，尽管问</span>
          <span class="prompt-audio">
            <span class="icon-wrap tiny-icon" v-html="getIcon('audio')"></span>
            语音
          </span>
        </button>

        <p class="hero-footnote">
          向 AI 聊天机器人 ChatGPT 发送消息即表示，你同意我们的
          <button class="inline-link" type="button" @click="openPanel('register')">服务条款</button>
          并已阅读我们的
          <button class="inline-link" type="button" @click="openPanel('register')">隐私政策</button>。
        </p>
      </section>
    </main>

    <div v-if="showAuthPanel" class="auth-overlay" @click.self="closePanel">
      <div class="auth-panel">
        <button class="auth-close" type="button" @click="closePanel" aria-label="关闭登录弹层">×</button>

        <div class="auth-brand">
          <component :is="LogoOpenai" class="auth-logo" />
          <div>
            <p class="auth-eyebrow">ChatGPT Mirror</p>
            <h2 class="auth-title">{{ isRegisterMode ? '创建帐户' : '欢迎回来' }}</h2>
          </div>
        </div>

        <div class="auth-tabs">
          <button
            class="auth-tab"
            :class="{ active: !isRegisterMode }"
            type="button"
            @click="switchPanel('login')"
          >
            登录
          </button>
          <button
            class="auth-tab"
            :class="{ active: isRegisterMode }"
            type="button"
            @click="switchPanel('register')"
          >
            注册
          </button>
        </div>

        <t-loading :loading="loading">
          <t-form ref="loginFormRef" :data="loginForm" :label-width="0" :rules="rules" @submit="onSubmit">
            <t-form-item name="username">
              <t-input v-model="loginForm.username" size="large" placeholder="用户名"></t-input>
            </t-form-item>

            <t-form-item name="password">
              <t-input
                v-model="loginForm.password"
                size="large"
                type="password"
                autocomplete="on"
                placeholder="密码"
              ></t-input>
            </t-form-item>

            <t-form-item v-if="isRegisterMode" name="chatgpt_token">
              <div class="token-field">
                <t-textarea
                  v-model="loginForm.chatgpt_token"
                  size="large"
                  placeholder="ChatGPT Cookies Token"
                ></t-textarea>
                <span class="token-hint">
                  Session Token 获取说明：
                  <t-link target="_blank" theme="primary" size="small" :href="ChatgptTokenTutorialUrl">
                    手动获取
                  </t-link>
                </span>
              </div>
            </t-form-item>

            <t-form-item>
              <button class="auth-submit" type="submit">
                {{ isRegisterMode ? '注册并进入' : '登录并进入' }}
              </button>
            </t-form-item>
          </t-form>
        </t-loading>

        <div class="auth-footer">
          <span>{{ isRegisterMode ? '已经拥有帐户？' : '没有帐户？' }}</span>
          <button class="inline-link" type="button" @click="switchPanel(isRegisterMode ? 'login' : 'register')">
            {{ isRegisterMode ? '登录' : '注册' }}
          </button>
          <span>或</span>
          <button class="inline-link inline-link-accent" type="button" @click="goFree">免费体验</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FormInstanceFunctions, FormProps, FormRule } from 'tdesign-vue-next';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import LogoOpenai from '@/assets/openai-logo.svg';
import { ChatgptTokenTutorialUrl } from '@/constants/index';
import { useUserStore } from '@/store';
import { redirectToConsumerChat } from '@/utils/direct-chat';

type PanelMode = 'login' | 'register' | null;

const iconMarkup: Record<string, string> = {
  panel:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="5" width="16" height="14" rx="3"></rect><path d="M9 5v14"></path></svg>',
  compose:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4l10-10-4-4L4 16v4Z"></path><path d="m13 7 4 4"></path></svg>',
  search:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="6"></circle><path d="m20 20-3.5-3.5"></path></svg>',
  image:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="5" width="16" height="14" rx="3"></rect><circle cx="9" cy="10" r="1.4"></circle><path d="m7 16 3-3 2.5 2.5L15 13l2 3"></path></svg>',
  apps:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="5" height="5" rx="1.2"></rect><rect x="14" y="5" width="5" height="5" rx="1.2"></rect><rect x="5" y="14" width="5" height="5" rx="1.2"></rect><rect x="14" y="14" width="5" height="5" rx="1.2"></rect></svg>',
  spark:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4"></path><path d="m6.5 8.5 2.8 2.8"></path><path d="M3 12h4"></path><path d="m6.5 15.5 2.8-2.8"></path><path d="M12 21v-4"></path><path d="m17.5 15.5-2.8-2.8"></path><path d="M21 12h-4"></path><path d="m17.5 8.5-2.8 2.8"></path></svg>',
  heart:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-6.7-4.3-8.4-8c-1.2-2.6.2-5.5 3-6.3 1.8-.5 3.7.1 5.1 1.6 1.4-1.5 3.3-2.1 5.1-1.6 2.8.8 4.2 3.7 3 6.3-1.7 3.7-8.4 8-8.4 8Z"></path></svg>',
  credit:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h16"></path><rect x="3" y="5" width="18" height="14" rx="3"></rect><path d="M7 15h4"></path></svg>',
  settings:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3.3"></circle><path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a1.8 1.8 0 0 1-2.5 2.5l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a1.8 1.8 0 0 1-3.6 0v-.1a1 1 0 0 0-.6-.9 1 1 0 0 0-1.1.2l-.1.1a1.8 1.8 0 1 1-2.5-2.5l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H6a1.8 1.8 0 0 1 0-3.6h.1a1 1 0 0 0 .9-.6 1 1 0 0 0-.2-1.1l-.1-.1a1.8 1.8 0 1 1 2.5-2.5l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4a1.8 1.8 0 0 1 3.6 0v.1a1 1 0 0 0 .6.9 1 1 0 0 0 1.1-.2l.1-.1a1.8 1.8 0 1 1 2.5 2.5l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6h.1a1.8 1.8 0 0 1 0 3.6h-.1a1 1 0 0 0-.9.6Z"></path></svg>',
  help:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"></circle><path d="M9.4 9a2.8 2.8 0 1 1 4.7 2c-.9.8-1.6 1.2-1.6 2.4"></path><path d="M12 16.8h.01"></path></svg>',
  chevron:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="m7 10 5 5 5-5"></path></svg>',
  plus:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"></path><path d="M5 12h14"></path></svg>',
  audio:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6v12"></path><path d="M8.5 9v6"></path><path d="M15.5 9v6"></path><path d="M5 11v2"></path><path d="M19 11v2"></path></svg>',
};

const primaryNav = [
  { label: '新聊天', icon: 'compose', shortcut: '⌘O' },
  { label: '搜索聊天', icon: 'search', shortcut: '⌘K' },
  { label: '图片', icon: 'image' },
  { label: '应用', icon: 'apps' },
  { label: '深度研究', icon: 'spark' },
  { label: 'Health', icon: 'heart' },
];

const secondaryNav = [
  { label: '查看套餐和定价', icon: 'credit' },
  { label: '设置', icon: 'settings' },
  { label: '帮助', icon: 'help' },
];

const userStore = useUserStore();
const route = useRoute();
const router = useRouter();

const loading = ref(false);
const panelMode = ref<PanelMode>(null);
const cfg = ref({ show_github: false, notice: '' });

const loginForm = reactive({
  username: '',
  password: '',
  chatgpt_token: undefined,
  invite_token: undefined,
  invite_id: undefined,
});

const loginFormRef = ref<FormInstanceFunctions | null>(null);

const rules: Record<string, FormRule[]> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  chatgpt_token: [
    { required: true, message: '请输入 Access Token 或 Session Token 或 Refresh Token', trigger: 'blur' },
  ],
};

const showAuthPanel = computed(() => panelMode.value !== null);
const isRegisterMode = computed(() => panelMode.value === 'register');

const getIcon = (name: string) => iconMarkup[name] || iconMarkup.compose;

const syncPanelFromRoute = (path: string) => {
  if (path.endsWith('/register') || path.endsWith('/invite_register')) {
    panelMode.value = 'register';
  } else if (path.endsWith('/login') && panelMode.value === 'register') {
    panelMode.value = null;
  }
};

onMounted(async () => {
  await getVersionCfg();
  syncPanelFromRoute(route.path);
});

watch(
  () => route.path,
  (path) => {
    syncPanelFromRoute(path);
  },
);

const switchPanel = async (mode: Exclude<PanelMode, null>) => {
  panelMode.value = mode;
  if (mode === 'register' && !route.path.endsWith('/invite_register') && !route.path.endsWith('/register')) {
    await router.replace({ name: 'register' });
  }
  if (mode === 'login' && route.path !== '/login') {
    await router.replace({ name: 'login' });
  }
};

const openPanel = async (mode: Exclude<PanelMode, null>) => {
  await switchPanel(mode);
};

const closePanel = async () => {
  panelMode.value = null;
  if (route.path !== '/login') {
    await router.replace({ name: 'login' });
  }
};

const onSubmit: FormProps['onSubmit'] = async ({ validateResult, firstError }) => {
  if (validateResult !== true) {
    console.error('表单引用未定义', firstError);
    return;
  }

  loading.value = true;
  let url = '/0x/user/login';

  if (isRegisterMode.value) {
    url = '/0x/user/register';
  }

  if (route.path.endsWith('/invite_register')) {
    const { hash } = window.location;
    const paramsString = hash.split('?')[1];
    const params = new URLSearchParams(paramsString);
    loginForm.invite_token = params.get('invite_token');
    loginForm.invite_id = params.get('id');
  }

  const data = await userStore.login(url, loginForm);
  if (data?.admin_token && data.is_admin) {
    router.push({ name: 'User' });
    return;
  }
  if (data?.admin_token) {
    const redirected = await redirectToConsumerChat();
    if (!redirected) {
      router.push({ name: 'LoginChatgpt' });
    }
    return;
  }

  loading.value = false;
};

const getVersionCfg = async () => {
  const response = await fetch('/0x/user/version-cfg');
  const data = await response.json();
  Object.assign(cfg.value, { ...data });
};

const goFree = async () => {
  loading.value = true;
  const data = await userStore.login('/0x/user/login-free', {});
  if (data?.admin_token) {
    const redirected = await redirectToConsumerChat();
    if (!redirected) {
      router.push({ name: 'LoginChatgpt' });
    }
    return;
  }

  loading.value = false;
};
</script>

<style scoped lang="less">
.entry-shell {
  display: flex;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(246, 248, 246, 0.92), rgba(255, 255, 255, 0.96) 35%),
    linear-gradient(180deg, #fbfbf8 0%, #fff 100%);
  color: #1f1f1f;
}

.entry-sidebar {
  display: flex;
  flex: 0 0 236px;
  flex-direction: column;
  justify-content: space-between;
  padding: 12px 14px;
  border-right: 1px solid rgba(18, 18, 18, 0.06);
  background: rgba(245, 245, 242, 0.88);
  backdrop-filter: blur(10px);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  color: #111;
}

.brand-logo {
  width: 22px;
  height: 22px;
}

.ghost-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: #666;
  cursor: pointer;
}

.ghost-icon:hover {
  background: rgba(17, 17, 17, 0.05);
  color: #111;
}

.sidebar-nav,
.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar-nav {
  flex: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 10px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #222;
  font-size: 15px;
  text-align: left;
  cursor: pointer;
}

.nav-link:hover {
  background: rgba(18, 18, 18, 0.05);
}

.nav-link-secondary {
  color: #343434;
}

.nav-label {
  flex: 1;
  min-width: 0;
}

.nav-shortcut {
  color: #8b8b8b;
  font-size: 12px;
}

.icon-wrap {
  display: inline-flex;
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
}

.icon-wrap :deep(svg) {
  width: 18px;
  height: 18px;
}

.signin-card {
  margin-top: 12px;
  padding-top: 16px;
  border-top: 1px solid rgba(18, 18, 18, 0.08);
}

.signin-title {
  margin: 0 0 8px;
  color: #212121;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.25;
}

.signin-copy {
  margin: 0 0 18px;
  color: #7a7a7a;
  font-size: 14px;
  line-height: 1.5;
}

.signin-button {
  width: 100%;
  height: 40px;
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: 999px;
  background: #fff;
  color: #111;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.signin-button:hover {
  background: #f7f7f5;
}

.signin-link,
.github-link {
  margin-top: 10px;
  color: #737373;
  font-size: 13px;
  text-decoration: none;
}

.signin-link {
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.signin-link:hover,
.github-link:hover {
  color: #111;
}

.notice-copy {
  margin-top: 12px;
  color: #777;
  font-size: 12px;
  line-height: 1.5;
}

.entry-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px 0 16px;
}

.model-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  border: none;
  background: transparent;
  color: #1e1e1e;
  font-size: 32px;
  font-weight: 700;
  cursor: pointer;
}

.topbar-actions {
  display: flex;
  gap: 10px;
}

.topbar-login,
.topbar-register {
  height: 38px;
  padding: 0 16px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.topbar-login {
  border: 1px solid #111;
  background: #111;
  color: #fff;
}

.topbar-register {
  border: 1px solid rgba(17, 17, 17, 0.12);
  background: rgba(255, 255, 255, 0.95);
  color: #111;
}

.hero {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 24px 44px;
}

.hero-title {
  margin: 0 0 44px;
  color: #181818;
  font-size: clamp(34px, 4vw, 52px);
  font-weight: 700;
  line-height: 1.08;
  text-align: center;
}

.prompt-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  width: min(700px, calc(100vw - 340px));
  min-height: 58px;
  padding: 10px 12px 10px 16px;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    0 18px 48px rgba(17, 17, 17, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
  color: #555;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.prompt-bar:hover {
  transform: translateY(-1px);
  border-color: rgba(17, 17, 17, 0.14);
  box-shadow: 0 22px 56px rgba(17, 17, 17, 0.08);
}

.prompt-leading {
  color: #4a4a4a;
}

.prompt-text {
  flex: 1;
  color: #666;
  font-size: 18px;
  text-align: left;
}

.prompt-audio {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border-radius: 999px;
  background: #f1f1ef;
  color: #2c2c2c;
  font-size: 15px;
  font-weight: 600;
}

.tiny-icon {
  width: 14px;
  height: 14px;
}

.tiny-icon :deep(svg) {
  width: 14px;
  height: 14px;
}

.hero-footnote {
  margin: 22px 0 0;
  color: #8b8b8b;
  font-size: 13px;
  text-align: center;
}

.inline-link {
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  font-size: inherit;
  font-weight: 600;
  cursor: pointer;
}

.inline-link:hover {
  color: #171717;
}

.inline-link-accent {
  color: #10a37f;
}

.auth-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(17, 17, 17, 0.28);
  backdrop-filter: blur(6px);
  z-index: 30;
}

.auth-panel {
  position: relative;
  width: min(460px, 100%);
  padding: 28px;
  border: 1px solid rgba(17, 17, 17, 0.06);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 28px 80px rgba(17, 17, 17, 0.16);
}

.auth-close {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 999px;
  background: #f4f4f2;
  color: #444;
  font-size: 20px;
  cursor: pointer;
}

.auth-brand {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 22px;
}

.auth-logo {
  width: 26px;
  height: 26px;
}

.auth-eyebrow {
  margin: 0 0 4px;
  color: #7d7d7d;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.auth-title {
  margin: 0;
  color: #181818;
  font-size: 28px;
  font-weight: 700;
}

.auth-tabs {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  background: #f5f5f2;
  margin-bottom: 22px;
}

.auth-tab {
  min-width: 88px;
  height: 36px;
  padding: 0 14px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #676767;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.auth-tab.active {
  background: #fff;
  color: #111;
  box-shadow: 0 4px 12px rgba(17, 17, 17, 0.06);
}

.token-field {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.token-hint {
  margin-top: 8px;
  color: #777;
  font-size: 12px;
}

.auth-submit {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 999px;
  background: #111;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.auth-submit:hover {
  background: #222;
}

.auth-footer {
  display: flex;
  gap: 6px;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
  color: #707070;
  font-size: 13px;
}

:deep(.t-form__item) {
  margin-bottom: 16px;
}

:deep(.t-input),
:deep(.t-textarea__inner) {
  border-radius: 18px;
}

:deep(.t-input) {
  height: 50px;
}

@media (max-width: 960px) {
  .entry-shell {
    flex-direction: column;
  }

  .entry-sidebar {
    flex: none;
    border-right: none;
    border-bottom: 1px solid rgba(18, 18, 18, 0.06);
  }

  .sidebar-nav {
    margin-bottom: 16px;
  }

  .hero {
    padding-top: 68px;
  }

  .prompt-bar {
    width: min(100%, 720px);
  }
}

@media (max-width: 640px) {
  .entry-sidebar {
    padding: 12px;
  }

  .topbar {
    padding: 14px 12px 0;
  }

  .model-switch {
    font-size: 24px;
  }

  .topbar-actions {
    gap: 8px;
  }

  .topbar-login,
  .topbar-register {
    padding: 0 12px;
    font-size: 13px;
  }

  .hero-title {
    margin-bottom: 28px;
    font-size: 32px;
  }

  .prompt-bar {
    min-height: 54px;
    padding: 8px 10px 8px 14px;
  }

  .prompt-text {
    font-size: 16px;
  }

  .prompt-audio {
    padding: 9px 12px;
    font-size: 14px;
  }

  .auth-panel {
    padding: 24px 18px 20px;
    border-radius: 24px;
  }

  .auth-brand {
    gap: 10px;
  }
}
</style>
