<template>
  <div class="redirect-shell">
    <div class="redirect-panel">
      <t-loading :loading="loading">
        <div class="redirect-copy">
          <p class="redirect-eyebrow">ChatGPT Mirror</p>
          <h1 class="redirect-title">{{ loading ? '正在进入对话' : '暂时无法进入对话' }}</h1>
          <p class="redirect-description">
            {{ loading ? '正在为当前账号创建会话并跳转到聊天界面。' : '当前账号还没有可用的对话通道，请联系管理员处理。' }}
          </p>
        </div>
      </t-loading>

      <div v-if="!loading" class="redirect-actions">
        <button class="redirect-btn redirect-btn-primary" type="button" @click="retry">重新尝试</button>
        <button class="redirect-btn" type="button" @click="backToLogin">返回登录</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { redirectToConsumerChat } from '@/utils/direct-chat';

const router = useRouter();
const loading = ref(true);

const startRedirect = async () => {
  loading.value = true;
  const redirected = await redirectToConsumerChat();
  if (!redirected) {
    loading.value = false;
  }
};

const retry = async () => {
  await startRedirect();
};

const backToLogin = () => {
  router.push({ name: 'login' });
};

onMounted(async () => {
  await startRedirect();
});
</script>

<style lang="less" scoped>
.redirect-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(246, 248, 246, 0.92), rgba(255, 255, 255, 0.96) 34%),
    linear-gradient(180deg, #fbfbf8 0%, #fff 100%);
}

.redirect-panel {
  width: min(560px, 100%);
  padding: 32px;
  border: 1px solid rgba(17, 17, 17, 0.06);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 28px 80px rgba(17, 17, 17, 0.12);
}

.redirect-copy {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.redirect-eyebrow {
  margin: 0;
  color: #7d7d79;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.redirect-title {
  margin: 0;
  color: #181818;
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 700;
  line-height: 1.05;
}

.redirect-description {
  margin: 0;
  color: #686863;
  font-size: 15px;
  line-height: 1.6;
}

.redirect-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.redirect-btn {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: 999px;
  background: #fff;
  color: #181818;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.redirect-btn-primary {
  border-color: #111;
  background: #111;
  color: #fff;
}
</style>
