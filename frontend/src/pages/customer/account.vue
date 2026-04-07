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
        <p v-else class="empty-copy">当前没有额外网页配额限制，可直接使用网页对话服务。</p>
        <div v-if="webQuotaWarnings.length" class="warning-stack">
          <p v-for="item in webQuotaWarnings" :key="item" class="warning-copy">{{ item }}</p>
        </div>
      </article>
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

interface SessionSummary {
  available: boolean;
  reason: string;
  pool_mode: string;
  isolated_session: boolean;
  web_quota_status: SessionQuotaStatus;
  api_quota_status: SessionQuotaStatus;
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
const usageSummary = ref<UsageSummary>({
  recent_records: [],
});
const sessionSummary = ref<SessionSummary>({
  available: false,
  reason: '',
  pool_mode: '',
  isolated_session: false,
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
});

const userInitial = computed(() => profile.value.username?.trim().charAt(0).toUpperCase() || 'U');
const quotaRules = computed(() => sessionSummary.value.web_quota_status.rules || []);
const webQuotaWarnings = computed(() => sessionSummary.value.web_quota_status.warnings || []);
const recentRecords = computed(() => usageSummary.value.recent_records || []);

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

.account-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.account-panel,
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

.section-kicker {
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
.rule-stack {
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
.rule-model {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.profile-hero p,
.plan-code,
.rule-meta,
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

.profile-matrix {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.profile-cell,
.rule-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 20px;
  background: rgba(245, 248, 244, 0.94);
}

.profile-cell span {
  color: #738379;
  font-size: 13px;
}

.plan-hero {
  padding: 18px;
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(243, 247, 244, 0.95), rgba(255, 255, 255, 0.92)),
    radial-gradient(circle at top right, rgba(147, 183, 155, 0.22), transparent 42%);
}

.plan-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.plan-state.ok {
  background: rgba(31, 142, 90, 0.12);
  color: #186742;
}

.plan-state.warn {
  background: rgba(209, 122, 42, 0.12);
  color: #8f5118;
}

.rule-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
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
  .account-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .account-panel,
  .records-panel {
    padding: 20px;
    border-radius: 24px;
  }

  .profile-matrix {
    grid-template-columns: 1fr;
  }

  .profile-cell,
  .rule-row {
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

  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
