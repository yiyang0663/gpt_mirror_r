<template>
  <div class="customer-home">
    <section class="hero-panel">
      <div class="hero-copy">
        <p class="hero-kicker">{{ profile.plan_name || 'Standard Access' }}</p>
        <h1 class="hero-title">{{ greeting }}</h1>
        <p class="hero-description">
          你的账号已接入站点统一维护的官方账号与中转账号。登录后无需再填任何 Token，系统会按后台配置直接分配可用通道。
        </p>

        <div class="hero-actions">
          <button class="hero-primary" type="button" @click="handleOpenChat">立即开始对话</button>
          <button class="hero-secondary" type="button" @click="router.push({ name: 'CustomerAccount' })">
            查看账户详情
          </button>
        </div>
      </div>

      <div class="hero-status">
        <div class="status-badge" :class="sessionReady ? 'ok' : 'warn'">
          <span class="status-dot"></span>
          {{ sessionReady ? '可立即进入对话' : sessionSummary.reason || '当前受限' }}
        </div>

        <div class="status-grid">
          <div v-for="item in summaryCards" :key="item.label" class="status-cell">
            <p class="status-label">{{ item.label }}</p>
            <p class="status-value">{{ item.value }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="overview-strip">
      <article class="overview-panel">
        <div class="section-head">
          <div>
            <p class="section-kicker">Access</p>
            <h2 class="section-title">当前账号状态</h2>
          </div>
        </div>

        <div class="detail-list">
          <div class="detail-row">
            <span>用户名</span>
            <strong>{{ profile.username || '-' }}</strong>
          </div>
          <div class="detail-row">
            <span>邮箱</span>
            <strong>{{ profile.email || '-' }}</strong>
          </div>
          <div class="detail-row">
            <span>套餐</span>
            <strong>{{ profile.plan_name || '未分配' }}</strong>
          </div>
          <div class="detail-row">
            <span>网页入口</span>
            <strong>{{ sessionSummary.available ? '可用' : '受限' }}</strong>
          </div>
          <div class="detail-row">
            <span>API 通道</span>
            <strong>{{ sessionSummary.api_quota_status.allowed ? '可用' : '受限' }}</strong>
          </div>
          <div class="detail-row">
            <span>账号池模式</span>
            <strong>{{ profile.pool_mode === 'specific_pools' ? '指定号池' : '公共账号池' }}</strong>
          </div>
          <div class="detail-row">
            <span>可用账号数</span>
            <strong>{{ profile.available_account_count || 0 }}</strong>
          </div>
          <div class="detail-row">
            <span>到期时间</span>
            <strong>{{ profile.expired_date || '长期有效' }}</strong>
          </div>
        </div>
      </article>

      <article class="overview-panel">
        <div class="section-head">
          <div>
            <p class="section-kicker">Quota</p>
            <h2 class="section-title">网页使用规则</h2>
          </div>
        </div>

        <div v-if="quotaRules.length" class="quota-stack">
          <div v-for="rule in quotaRules" :key="`${rule.rule_id}-${rule.period}-${rule.channel}-${rule.model_name}`" class="quota-item">
            <div>
              <p class="quota-model">{{ rule.model_name || '全部模型' }}</p>
              <p class="quota-meta">
                {{ formatChannel(rule.channel) }} / {{ formatPeriod(rule.period) }}
                <span v-if="rule.usage_source === 'gateway_daily_requests'"> · 按 gateway 当日请求数</span>
              </p>
            </div>
            <div class="quota-metrics">
              <span>{{ formatLimit(rule.used_requests, rule.request_limit, '次') }}</span>
              <span>{{ formatLimit(rule.used_tokens, rule.token_limit, 'tokens') }}</span>
            </div>
          </div>
        </div>
        <p v-else class="empty-copy">当前套餐未配置显式网页配额规则，默认按后台账号池可用性提供服务。</p>
        <div v-if="webQuotaWarnings.length" class="warning-stack">
          <p v-for="item in webQuotaWarnings" :key="item" class="warning-copy">{{ item }}</p>
        </div>
      </article>
    </section>

    <section class="session-panel">
      <div class="section-head">
        <div>
          <p class="section-kicker">Session</p>
          <h2 class="section-title">接入资源摘要</h2>
        </div>
      </div>

      <div class="session-grid">
        <article class="session-card">
          <p class="session-label">推荐通道</p>
          <p class="session-value">{{ sessionSummary.recommended_account?.chatgpt_username || '暂未分配' }}</p>
          <p class="session-meta">
            {{
              sessionSummary.recommended_account
                ? `${formatSourceType(sessionSummary.recommended_account.source_type)} · ${formatHealth(sessionSummary.recommended_account.health_status)}`
                : sessionSummary.reason || '等待管理员分配可用通道'
            }}
          </p>

          <div class="session-stats">
            <div class="session-stat">
              <span>网页官方</span>
              <strong>{{ sessionSummary.available_accounts.web_official || 0 }}</strong>
            </div>
            <div class="session-stat">
              <span>网页中转</span>
              <strong>{{ sessionSummary.available_accounts.web_relay || 0 }}</strong>
            </div>
          </div>
        </article>

        <article class="session-card">
          <p class="session-label">号池与模型</p>
          <div v-if="sessionSummary.bound_pools.length" class="chip-list">
            <span v-for="pool in sessionSummary.bound_pools" :key="pool.id" class="chip">
              {{ pool.car_name }} · {{ pool.account_count }} 个账号
            </span>
          </div>
          <p v-else class="empty-copy">当前使用站点公共账号池。</p>

          <div class="model-group">
            <span v-for="item in sessionSummary.supported_models" :key="item" class="model-chip">{{ item }}</span>
            <span v-if="!sessionSummary.supported_models.length" class="empty-copy">当前未设置显式模型白名单。</span>
          </div>
        </article>

        <article class="session-card">
          <p class="session-label">最近调度</p>
          <div v-if="sessionRoutes.length" class="dispatch-list">
            <div v-for="item in sessionRoutes" :key="item.id" class="dispatch-row">
              <div>
                <p class="dispatch-title">{{ formatEntrypoint(item.entrypoint) }}</p>
                <p class="dispatch-meta">
                  {{ item.account?.chatgpt_username || '未命中账号' }} · {{ TimestampToDate(item.created_time * 1000) }}
                </p>
              </div>
              <span class="dispatch-tag" :class="item.decision_status === 'selected' ? 'success' : 'warn'">
                {{ formatDecisionStatus(item.decision_status) }}
              </span>
            </div>
          </div>
          <p v-else class="empty-copy">最近还没有调度记录。</p>
        </article>
      </div>
    </section>

    <section class="activity-panel">
      <div class="section-head">
        <div>
          <p class="section-kicker">Recent</p>
          <h2 class="section-title">最近调用</h2>
        </div>
        <button class="inline-nav" type="button" @click="router.push({ name: 'CustomerAccount' })">查看全部</button>
      </div>

      <div v-if="recentRecords.length" class="activity-list">
        <div v-for="item in recentRecords" :key="item.id" class="activity-row">
          <div>
            <p class="activity-model">{{ item.model_name || '未标记模型' }}</p>
            <p class="activity-meta">{{ item.chatgpt_username || '系统账号' }} · {{ TimestampToDate(item.created_at * 1000) }}</p>
          </div>
          <div class="activity-side">
            <span class="activity-tokens">{{ item.total_tokens }} tokens</span>
            <span class="activity-status" :class="item.status_code >= 200 && item.status_code < 400 ? 'success' : 'danger'">
              {{ item.status_code || '-' }}
            </span>
          </div>
        </div>
      </div>
      <p v-else class="empty-copy">还没有调用记录。点击上方按钮即可开始第一次对话。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import RequestApi from '@/api/request';
import { TimestampToDate } from '@/utils/date';
import { redirectToConsumerChat } from '@/utils/direct-chat';

interface QuotaRuleStatus {
  rule_id: number;
  model_name: string;
  channel: string;
  period: string;
  request_limit: number;
  token_limit: number;
  used_requests: number;
  used_tokens: number;
  usage_source?: string;
  usage_note?: string;
  request_limit_enforced?: boolean;
  token_limit_enforced?: boolean;
}

interface SessionQuotaStatus {
  allowed: boolean;
  reason: string;
  plan_name: string;
  plan_code: string;
  rules: QuotaRuleStatus[];
  warnings: string[];
}

interface ProfileData {
  username: string;
  email: string;
  status: string;
  plan_name: string;
  plan_code: string;
  pool_mode?: string;
  available_account_count: number;
  expired_date: string | null;
  date_joined: string;
  last_login: string | null;
}

interface UsageRecord {
  id: number;
  chatgpt_username: string;
  model_name: string;
  total_tokens: number;
  status_code: number;
  created_at: number;
}

interface UsageSummary {
  total_requests: number;
  success_requests: number;
  failed_requests: number;
  total_tokens: number;
  estimated_cost: number;
  recent_records: UsageRecord[];
}

interface SessionBoundPool {
  id: number;
  car_name: string;
  account_count: number;
}

interface SessionAccount {
  id: number;
  chatgpt_username: string;
  account_type: string;
  source_type: string;
  health_status: string;
  plan_type: string;
}

interface SessionDispatch {
  id: number;
  entrypoint: string;
  channel: string;
  model_name: string;
  decision_status: string;
  reason: string;
  created_time: number;
  candidate_count: number;
  account: SessionAccount | null;
}

interface SessionSummary {
  available: boolean;
  reason: string;
  pool_mode: string;
  isolated_session: boolean;
  bound_pools: SessionBoundPool[];
  web_quota_status: SessionQuotaStatus;
  api_quota_status: SessionQuotaStatus;
  available_accounts: {
    web_total: number;
    api_total: number;
    web_official: number;
    web_relay: number;
    api_official: number;
    api_relay: number;
    web_candidates: number;
    api_candidates: number;
  };
  supported_models: string[];
  recommended_account: SessionAccount | null;
  recent_dispatches: SessionDispatch[];
}

const router = useRouter();
const profile = ref<ProfileData>({
  username: '',
  email: '',
  status: '',
  plan_name: '',
  plan_code: '',
  pool_mode: '',
  available_account_count: 0,
  expired_date: null,
  date_joined: '',
  last_login: null,
});
const usageSummary = ref<UsageSummary>({
  total_requests: 0,
  success_requests: 0,
  failed_requests: 0,
  total_tokens: 0,
  estimated_cost: 0,
  recent_records: [],
});
const sessionSummary = ref<SessionSummary>({
  available: false,
  reason: '',
  pool_mode: '',
  isolated_session: false,
  bound_pools: [],
  web_quota_status: {
    allowed: true,
    reason: '',
    plan_name: '',
    plan_code: '',
    rules: [],
    warnings: [],
  },
  api_quota_status: {
    allowed: true,
    reason: '',
    plan_name: '',
    plan_code: '',
    rules: [],
    warnings: [],
  },
  available_accounts: {
    web_total: 0,
    api_total: 0,
    web_official: 0,
    web_relay: 0,
    api_official: 0,
    api_relay: 0,
    web_candidates: 0,
    api_candidates: 0,
  },
  supported_models: [],
  recommended_account: null,
  recent_dispatches: [],
});

const greeting = computed(() => {
  return profile.value.username ? `${profile.value.username}，今天继续聊点什么？` : '欢迎回来，今天继续聊点什么？';
});

const sessionReady = computed(() => sessionSummary.value.available);
const quotaRules = computed(() => sessionSummary.value.web_quota_status.rules || []);
const webQuotaWarnings = computed(() => sessionSummary.value.web_quota_status.warnings || []);
const recentRecords = computed(() => usageSummary.value.recent_records?.slice(0, 6) || []);
const sessionRoutes = computed(() => sessionSummary.value.recent_dispatches || []);

const summaryCards = computed(() => [
  { label: '网页通道', value: sessionSummary.value.available_accounts.web_total || 0 },
  { label: 'API 通道', value: sessionSummary.value.available_accounts.api_total || 0 },
  { label: '累计请求', value: usageSummary.value.total_requests || 0 },
  { label: '累计 Tokens', value: usageSummary.value.total_tokens || 0 },
]);

const formatChannel = (channel: string) => {
  if (channel === 'api') return 'API';
  if (channel === 'web') return '网页';
  return '全部渠道';
};

const formatPeriod = (period: string) => {
  return period === 'daily' ? '每日' : '每月';
};

const formatLimit = (used: number, limit: number, suffix: string) => {
  if (!limit) return `${used} ${suffix} / 不限`;
  return `${used} ${suffix} / ${limit} ${suffix}`;
};

const formatSourceType = (value: string) => {
  if (value === 'relay') return '中转站';
  return '官方账号';
};

const formatHealth = (value: string) => {
  if (value === 'down') return '不可用';
  if (value === 'degraded') return '降级';
  return '健康';
};

const formatDecisionStatus = (value: string) => {
  if (value === 'selected') return '已命中';
  if (value === 'rejected') return '已拦截';
  return '未命中';
};

const formatEntrypoint = (value: string) => {
  if (value === 'get_mirror_token') return '直聊入口';
  if (value === 'user_chatgpt_list') return '账号列表';
  if (value === 'chatgpt_login') return '网页登录';
  return value || '系统调度';
};

const getProfile = async () => {
  const response = await RequestApi('/0x/user/me');
  if (!response.ok) return;
  profile.value = await response.json();
};

const getUsageSummary = async () => {
  const response = await RequestApi('/0x/user/usage-summary');
  if (!response.ok) return;
  usageSummary.value = await response.json();
};

const getSessionSummary = async () => {
  const response = await RequestApi('/0x/user/session-summary');
  if (!response.ok) return;
  sessionSummary.value = await response.json();
};

const handleOpenChat = async () => {
  await redirectToConsumerChat();
};

onMounted(async () => {
  await Promise.all([getProfile(), getUsageSummary(), getSessionSummary()]);
});
</script>

<style scoped lang="less">
.customer-home {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-panel,
.overview-panel,
.session-panel,
.activity-panel {
  border: 1px solid rgba(20, 28, 23, 0.08);
  background: rgba(255, 255, 255, 0.68);
  box-shadow:
    0 26px 70px rgba(20, 28, 23, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(18px);
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 28px;
  padding: 32px;
  border-radius: 34px;
}

.hero-kicker,
.section-kicker,
.session-label {
  margin: 0 0 10px;
  color: #78907e;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  max-width: 12ch;
  margin: 0;
  font-size: clamp(34px, 5vw, 58px);
  font-weight: 700;
  line-height: 0.96;
  letter-spacing: -0.04em;
}

.hero-description {
  max-width: 56ch;
  margin: 18px 0 0;
  color: #5d7063;
  font-size: 15px;
  line-height: 1.65;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 24px;
}

.hero-primary,
.hero-secondary,
.inline-nav {
  min-height: 48px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.hero-primary {
  border: none;
  background: #18231d;
  color: #fff;
}

.hero-secondary,
.inline-nav {
  border: 1px solid rgba(24, 35, 29, 0.12);
  background: rgba(255, 255, 255, 0.84);
  color: #1d2b24;
}

.hero-status {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(242, 247, 243, 0.95), rgba(255, 255, 255, 0.9)),
    radial-gradient(circle at top right, rgba(150, 185, 158, 0.24), transparent 45%);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 8px;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.status-badge.ok,
.dispatch-tag.success,
.activity-status.success {
  background: rgba(31, 142, 90, 0.12);
  color: #186742;
}

.status-badge.warn,
.dispatch-tag.warn {
  background: rgba(209, 122, 42, 0.12);
  color: #8f5118;
}

.activity-status.danger {
  background: rgba(189, 69, 69, 0.12);
  color: #973030;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.status-cell {
  padding: 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.78);
}

.status-label {
  margin: 0 0 8px;
  color: #748579;
  font-size: 12px;
}

.status-value {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.overview-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.overview-panel,
.session-panel,
.activity-panel {
  padding: 24px;
  border-radius: 30px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.section-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.05;
}

.detail-list,
.quota-stack,
.activity-list,
.dispatch-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row,
.quota-item,
.activity-row,
.dispatch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 20px;
  background: rgba(246, 248, 244, 0.9);
}

.detail-row span,
.quota-meta,
.activity-meta,
.dispatch-meta,
.session-meta {
  color: #728378;
  font-size: 13px;
}

.quota-model,
.activity-model,
.dispatch-title {
  margin: 0 0 5px;
  font-size: 15px;
  font-weight: 700;
}

.quota-metrics,
.activity-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.activity-tokens {
  font-size: 14px;
  font-weight: 700;
}

.activity-status,
.dispatch-tag {
  min-width: 52px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.session-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.session-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(246, 248, 244, 0.9);
}

.session-value {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.08;
  word-break: break-word;
}

.session-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.session-stat {
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
}

.session-stat span {
  display: block;
  color: #748579;
  font-size: 12px;
}

.session-stat strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
  line-height: 1;
}

.chip-list,
.model-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip,
.model-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.84);
  color: #244033;
  font-size: 12px;
  font-weight: 700;
}

.empty-copy {
  margin: 0;
  color: #718276;
  font-size: 14px;
  line-height: 1.7;
}

.warning-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 14px;
}

.warning-copy {
  margin: 0;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(209, 122, 42, 0.1);
  color: #8f5118;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 1080px) {
  .hero-panel,
  .overview-strip,
  .session-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .hero-panel,
  .overview-panel,
  .session-panel,
  .activity-panel {
    padding: 20px;
    border-radius: 24px;
  }

  .hero-actions {
    flex-direction: column;
  }

  .hero-primary,
  .hero-secondary,
  .inline-nav {
    width: 100%;
  }

  .status-grid,
  .session-stats {
    grid-template-columns: 1fr;
  }

  .detail-row,
  .quota-item,
  .activity-row,
  .dispatch-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .quota-metrics,
  .activity-side {
    align-items: flex-start;
  }
}
</style>
