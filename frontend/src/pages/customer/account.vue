<template>
  <div class="customer-account">
    <section class="account-grid">
      <article class="account-panel">
        <div class="section-head">
          <div>
            <p class="section-kicker">Profile</p>
            <h2 class="section-title">账户资料</h2>
          </div>
        </div>

        <div class="profile-stack">
          <div class="profile-hero">
            <span class="profile-badge">{{ userInitial }}</span>
            <div>
              <h3>{{ profile.username || '用户' }}</h3>
              <p>{{ profile.email || '未填写邮箱' }}</p>
            </div>
          </div>

          <div class="profile-matrix">
            <div class="profile-cell">
              <span>账号状态</span>
              <strong>{{ formatStatus(profile.status) }}</strong>
            </div>
            <div class="profile-cell">
              <span>最近登录</span>
              <strong>{{ profile.last_login || '首次使用' }}</strong>
            </div>
            <div class="profile-cell">
              <span>注册时间</span>
              <strong>{{ profile.date_joined || '-' }}</strong>
            </div>
            <div class="profile-cell">
              <span>账号池</span>
              <strong>{{ profile.pool_mode === 'specific_pools' ? '指定号池' : '公共账号池' }}</strong>
            </div>
            <div class="profile-cell">
              <span>可用账号数</span>
              <strong>{{ profile.available_account_count || 0 }}</strong>
            </div>
            <div class="profile-cell">
              <span>会话隔离</span>
              <strong>{{ profile.isolated_session ? '独立会话' : '共享会话' }}</strong>
            </div>
          </div>
        </div>
      </article>

      <article class="account-panel">
        <div class="section-head">
          <div>
            <p class="section-kicker">Plan</p>
            <h2 class="section-title">套餐与额度</h2>
          </div>
        </div>

        <div class="plan-hero">
          <p class="plan-name">{{ profile.plan_name || sessionSummary.web_quota_status.plan_name || '未分配套餐' }}</p>
          <p class="plan-code">{{ profile.plan_code || sessionSummary.web_quota_status.plan_code || 'no-plan' }}</p>
          <p class="plan-state" :class="sessionSummary.available ? 'ok' : 'warn'">
            {{ sessionSummary.available ? '当前可进入网页对话' : sessionSummary.reason || '当前使用受限' }}
          </p>
        </div>

        <div v-if="quotaRules.length" class="rule-stack">
          <div v-for="rule in quotaRules" :key="`${rule.rule_id}-${rule.period}-${rule.channel}-${rule.model_name}`" class="rule-row">
            <div>
              <p class="rule-model">{{ rule.model_name || '全部模型' }}</p>
              <p class="rule-meta">
                {{ formatChannel(rule.channel) }} / {{ formatPeriod(rule.period) }}
                <span v-if="rule.usage_source === 'gateway_daily_requests'"> · 按 gateway 当日请求数</span>
              </p>
            </div>
            <div class="rule-side">
              <span>{{ formatUsage(rule.used_requests, rule.request_limit, '次') }}</span>
              <span>{{ formatUsage(rule.used_tokens, rule.token_limit, 'tokens') }}</span>
            </div>
          </div>
        </div>
        <p v-else class="empty-copy">当前没有额外网页配额限制，默认按站点账号池状态提供服务。</p>
        <div v-if="webQuotaWarnings.length" class="warning-stack">
          <p v-for="item in webQuotaWarnings" :key="item" class="warning-copy">{{ item }}</p>
        </div>
      </article>
    </section>

    <section class="access-panel">
      <div class="section-head">
        <div>
          <p class="section-kicker">Session</p>
          <h2 class="section-title">接入会话</h2>
        </div>
        <button class="chat-link" type="button" @click="handleOpenChat">开始新对话</button>
      </div>

      <div class="access-grid">
        <article class="access-card">
          <p class="access-label">入口状态</p>
          <div class="access-matrix">
            <div class="access-stat">
              <span>网页入口</span>
              <strong>{{ sessionSummary.available ? '可用' : '受限' }}</strong>
            </div>
            <div class="access-stat">
              <span>API 通道</span>
              <strong>{{ sessionSummary.api_quota_status.allowed ? '可用' : '受限' }}</strong>
            </div>
            <div class="access-stat">
              <span>推荐账号</span>
              <strong>{{ sessionSummary.recommended_account?.chatgpt_username || '暂未分配' }}</strong>
            </div>
            <div class="access-stat">
              <span>网页候选</span>
              <strong>{{ sessionSummary.available_accounts.web_candidates || 0 }}</strong>
            </div>
          </div>
        </article>

        <article class="access-card">
          <p class="access-label">号池与模型</p>
          <div v-if="sessionSummary.bound_pools.length" class="chip-list">
            <span v-for="pool in sessionSummary.bound_pools" :key="pool.id" class="chip">
              {{ pool.car_name }} · {{ pool.account_count }} 个账号
            </span>
          </div>
          <p v-else class="empty-copy">当前使用站点公共账号池。</p>

          <div class="chip-list">
            <span v-for="item in sessionSummary.supported_models" :key="item" class="chip chip-model">{{ item }}</span>
            <span v-if="!sessionSummary.supported_models.length" class="empty-copy">当前未设置显式模型白名单。</span>
          </div>

          <div v-if="recentDispatches.length" class="dispatch-list">
            <div v-for="item in recentDispatches" :key="item.id" class="dispatch-row">
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
        </article>
      </div>
    </section>

    <section class="records-panel">
      <div class="section-head">
        <div>
          <p class="section-kicker">History</p>
          <h2 class="section-title">最近 20 次请求</h2>
        </div>
      </div>

      <div v-if="recentRecords.length" class="record-table">
        <div class="record-head">
          <span>模型</span>
          <span>上游账号</span>
          <span>Tokens</span>
          <span>状态</span>
          <span>时间</span>
        </div>
        <div v-for="item in recentRecords" :key="item.id" class="record-row">
          <span>{{ item.model_name || '未标记模型' }}</span>
          <span>{{ item.chatgpt_username || '系统账号' }}</span>
          <span>{{ item.total_tokens }}</span>
          <span :class="item.status_code >= 200 && item.status_code < 400 ? 'success' : 'danger'">
            {{ item.status_code || '-' }}
          </span>
          <span>{{ TimestampToDate(item.created_at * 1000) }}</span>
        </div>
      </div>
      <p v-else class="empty-copy">还没有请求记录。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import RequestApi from '@/api/request';
import { TimestampToDate } from '@/utils/date';

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
  available_account_count: number;
  pool_mode: string;
  isolated_session: boolean;
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

const profile = ref<ProfileData>({
  username: '',
  email: '',
  status: '',
  plan_name: '',
  plan_code: '',
  available_account_count: 0,
  pool_mode: '',
  isolated_session: false,
  date_joined: '',
  last_login: null,
});
const router = useRouter();
const usageSummary = ref<UsageSummary>({
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

const userInitial = computed(() => profile.value.username?.trim().charAt(0).toUpperCase() || 'U');
const quotaRules = computed(() => sessionSummary.value.web_quota_status.rules || []);
const webQuotaWarnings = computed(() => sessionSummary.value.web_quota_status.warnings || []);
const recentRecords = computed(() => usageSummary.value.recent_records || []);
const recentDispatches = computed(() => sessionSummary.value.recent_dispatches.slice(0, 6) || []);

const formatStatus = (status: string) => {
  if (status === 'disabled') return '已停用';
  if (status === 'expired') return '已过期';
  return '正常';
};

const formatChannel = (channel: string) => {
  if (channel === 'api') return 'API';
  if (channel === 'web') return '网页';
  return '全部渠道';
};

const formatPeriod = (period: string) => {
  return period === 'daily' ? '每日' : '每月';
};

const formatUsage = (used: number, limit: number, suffix: string) => {
  if (!limit) return `${used} ${suffix} / 不限`;
  return `${used} ${suffix} / ${limit} ${suffix}`;
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
  await router.push({ name: 'CustomerChat' });
};

onMounted(async () => {
  await Promise.all([getProfile(), getUsageSummary(), getSessionSummary()]);
});
</script>

<style scoped lang="less">
.customer-account {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.account-grid,
.access-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.account-panel,
.access-panel,
.records-panel {
  padding: 24px;
  border: 1px solid rgba(20, 28, 23, 0.08);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.68);
  box-shadow:
    0 24px 64px rgba(20, 28, 23, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(18px);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.section-kicker,
.access-label {
  margin: 0 0 10px;
  color: #78907e;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.section-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.05;
}

.profile-stack,
.rule-stack,
.dispatch-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.profile-hero {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border-radius: 24px;
  background: rgba(245, 248, 244, 0.94);
}

.profile-hero h3,
.plan-name,
.rule-model,
.dispatch-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.profile-hero p,
.plan-code,
.rule-meta,
.dispatch-meta,
.empty-copy {
  margin: 6px 0 0;
  color: #738379;
  font-size: 13px;
}

.profile-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #18231d;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
}

.profile-matrix,
.access-matrix {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.profile-cell,
.rule-row,
.access-stat,
.dispatch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 20px;
  background: rgba(245, 248, 244, 0.94);
}

.profile-cell span,
.access-stat span {
  color: #738379;
  font-size: 13px;
}

.access-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(245, 248, 244, 0.94);
}

.plan-hero {
  padding: 18px;
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(243, 247, 244, 0.95), rgba(255, 255, 255, 0.92)),
    radial-gradient(circle at top right, rgba(147, 183, 155, 0.22), transparent 42%);
}

.plan-state,
.dispatch-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.plan-state.ok,
.dispatch-tag.success {
  background: rgba(31, 142, 90, 0.12);
  color: #186742;
}

.plan-state.warn,
.dispatch-tag.warn {
  background: rgba(209, 122, 42, 0.12);
  color: #8f5118;
}

.rule-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
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

.chat-link {
  min-height: 44px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  background: #18231d;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.record-table {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.record-head,
.record-row {
  display: grid;
  grid-template-columns: 1.2fr 1.2fr 0.7fr 0.7fr 1fr;
  gap: 12px;
  align-items: center;
}

.record-head {
  padding: 0 4px;
  color: #708176;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.record-row {
  padding: 14px 16px;
  border-radius: 20px;
  background: rgba(245, 248, 244, 0.94);
  font-size: 14px;
}

.record-row .success {
  color: #186742;
  font-weight: 700;
}

.record-row .danger {
  color: #973030;
  font-weight: 700;
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
  .account-grid,
  .access-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .account-panel,
  .access-panel,
  .records-panel {
    padding: 20px;
    border-radius: 24px;
  }

  .profile-matrix,
  .access-matrix {
    grid-template-columns: 1fr;
  }

  .profile-cell,
  .rule-row,
  .access-stat,
  .dispatch-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .rule-side {
    align-items: flex-start;
  }

  .record-head {
    display: none;
  }

  .record-row {
    grid-template-columns: 1fr;
  }

  .chat-link {
    width: 100%;
  }

  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
