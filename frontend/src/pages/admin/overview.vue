<template>
  <div class="ops-page">
    <admin-page-intro
      eyebrow="Operations Console"
      title="后台总览"
      description="把用户、上游账号、号池、套餐和今日流量放到同一个运营视图里，便于值守和调度。"
    >
      <template #actions>
        <t-button theme="primary" :loading="loading" @click="loadOverview">刷新概览</t-button>
        <t-button variant="outline" theme="default" @click="router.push('/account/chatgpt')">管理上游账号</t-button>
      </template>
    </admin-page-intro>

    <admin-metric-grid :items="heroMetrics" />

    <div class="ops-section-grid">
      <t-card class="list-card-container">
        <div class="ops-surface__head">
          <div>
            <h3>资源态势</h3>
            <p>快速判断用户、上游资源和套餐供给是否均衡。</p>
          </div>
          <span class="ops-surface__badge">更新至 {{ overview.today || '-' }}</span>
        </div>

        <div class="ops-subgrid">
          <div class="ops-subpanel">
            <div class="ops-subpanel__label">用户与订阅</div>
            <div class="ops-stat-row">
              <strong>{{ overview.users.total }}</strong>
              <span>总用户</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.users.active }}</strong>
              <span>可用用户</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.users.expiring_soon }}</strong>
              <span>7 天内到期</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.users.specific_pool }}</strong>
              <span>使用指定号池</span>
            </div>
          </div>

          <div class="ops-subpanel">
            <div class="ops-subpanel__label">上游供给</div>
            <div class="ops-stat-row">
              <strong>{{ overview.accounts.total }}</strong>
              <span>总账号源</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.accounts.available }}</strong>
              <span>可调度账号</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.accounts.relay }}</strong>
              <span>中转账号</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.pools.total }}</strong>
              <span>账号池</span>
            </div>
          </div>
        </div>
      </t-card>

      <t-card class="list-card-container">
        <div class="ops-surface__head">
          <div>
            <h3>今日运行</h3>
            <p>观察当天请求量、失败量和同步状态，便于排查当前波动。</p>
          </div>
          <span class="ops-surface__badge">实时</span>
        </div>

        <div class="ops-subgrid">
          <div class="ops-subpanel">
            <div class="ops-subpanel__label">请求与调度</div>
            <div class="ops-stat-row">
              <strong>{{ overview.traffic.today_requests }}</strong>
              <span>今日请求</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.traffic.today_failed_requests }}</strong>
              <span>失败请求</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.traffic.today_dispatch_empty }}</strong>
              <span>无可用账号</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.sync.today_dispatch_selected }}</strong>
              <span>成功调度</span>
            </div>
          </div>

          <div class="ops-subpanel">
            <div class="ops-subpanel__label">同步与访问</div>
            <div class="ops-stat-row">
              <strong>{{ overview.sync.synced_user_count }}</strong>
              <span>已同步用户</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.sync.today_request_snapshot }}</strong>
              <span>网页请求快照</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ overview.sync.today_login_count }}</strong>
              <span>今日登录</span>
            </div>
            <div class="ops-stat-row">
              <strong>{{ formatTimestamp(overview.sync.latest_sync_at) }}</strong>
              <span>最近同步</span>
            </div>
          </div>
        </div>
      </t-card>
    </div>

    <div class="ops-section-grid ops-section-grid--wide">
      <t-card class="list-card-container">
        <div class="ops-surface__head">
          <div>
            <h3>最近变更</h3>
            <p>优先处理最近新增用户和最近更新的上游账号。</p>
          </div>
        </div>

        <div class="ops-table-dual">
          <div class="ops-subpanel">
            <div class="ops-subpanel__label">最新用户</div>
            <div v-if="overview.recent_users.length" class="ops-list">
              <div v-for="item in overview.recent_users" :key="item.id" class="ops-list-item">
                <div>
                  <strong>{{ item.username }}</strong>
                  <span>{{ item.email || '未填写邮箱' }}</span>
                </div>
                <div class="ops-list-item__meta">
                  <t-tag :theme="item.is_active ? 'success' : 'warning'" variant="light">
                    {{ item.is_active ? '启用' : '停用' }}
                  </t-tag>
                  <span>{{ formatDateTime(item.date_joined) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="ops-empty">暂无用户数据</div>
          </div>

          <div class="ops-subpanel">
            <div class="ops-subpanel__label">最近更新账号</div>
            <div v-if="overview.recent_accounts.length" class="ops-list">
              <div v-for="item in overview.recent_accounts" :key="item.id" class="ops-list-item">
                <div>
                  <strong>{{ item.chatgpt_username }}</strong>
                  <span>{{ item.plan_type || '未标记类型' }}</span>
                </div>
                <div class="ops-list-item__meta">
                  <t-tag :theme="item.auth_status ? 'success' : 'danger'" variant="light">
                    {{ item.auth_status ? '可用' : '失效' }}
                  </t-tag>
                  <span>{{ formatTimestamp(item.updated_time) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="ops-empty">暂无账号数据</div>
          </div>
        </div>
      </t-card>

      <t-card class="list-card-container">
        <div class="ops-surface__head">
          <div>
            <h3>热点与登录</h3>
            <p>最近的模型流量和当日登录活动。</p>
          </div>
        </div>

        <div class="ops-table-dual">
          <div class="ops-subpanel">
            <div class="ops-subpanel__label">今日热门模型</div>
            <div v-if="overview.traffic.top_models.length" class="ops-list">
              <div v-for="item in overview.traffic.top_models" :key="item.model_name" class="ops-list-item">
                <div>
                  <strong>{{ item.model_name }}</strong>
                  <span>{{ item.request_count }} 次请求</span>
                </div>
                <div class="ops-list-item__meta">
                  <span>{{ item.total_tokens }} tokens</span>
                </div>
              </div>
            </div>
            <div v-else class="ops-empty">暂无模型热点</div>
          </div>

          <div class="ops-subpanel">
            <div class="ops-subpanel__label">今日登录活动</div>
            <div v-if="overview.recent_logins.length" class="ops-list">
              <div
                v-for="item in overview.recent_logins"
                :key="`${item.username}-${item.created_at}-${item.ip}`"
                class="ops-list-item"
              >
                <div>
                  <strong>{{ item.username }}</strong>
                  <span>{{ item.ip }}</span>
                </div>
                <div class="ops-list-item__meta">
                  <t-tag variant="light">{{ item.log_type }}</t-tag>
                  <span>{{ formatTimestamp(item.created_at) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="ops-empty">暂无登录活动</div>
          </div>
        </div>
      </t-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import dayjs from 'dayjs';
import { ChartIcon, DataDisplayIcon, MoneyIcon, NotificationIcon } from 'tdesign-icons-vue-next';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import RequestApi from '@/api/request';
import AdminMetricGrid from '@/components/admin/AdminMetricGrid.vue';
import AdminPageIntro from '@/components/admin/AdminPageIntro.vue';
import { TimestampToDate } from '@/utils/date';

interface OverviewLine {
  id?: number;
  model_name?: string;
  request_count?: number;
  total_tokens?: number;
  username?: string;
  email?: string;
  status?: string;
  is_active?: boolean;
  date_joined?: string;
  chatgpt_username?: string;
  auth_status?: boolean;
  plan_type?: string;
  updated_time?: number;
  ip?: string;
  log_type?: string;
  created_at?: number;
}

interface OverviewPayload {
  today: string;
  users: {
    total: number;
    active: number;
    specific_pool: number;
    expiring_soon: number;
  };
  accounts: {
    total: number;
    available: number;
    healthy: number;
    relay: number;
    web_enabled: number;
    api_enabled: number;
  };
  pools: {
    total: number;
    non_empty: number;
    account_slots: number;
    bound_users: number;
  };
  plans: {
    total: number;
    active: number;
    web_enabled: number;
    api_enabled: number;
  };
  traffic: {
    today_requests: number;
    today_failed_requests: number;
    today_total_tokens: number;
    today_estimated_cost: number;
    today_unique_users: number;
    today_dispatch_empty: number;
    top_models: OverviewLine[];
  };
  sync: {
    synced_user_count: number;
    today_request_snapshot: number;
    latest_sync_at: number;
    today_login_count: number;
    today_dispatch_selected: number;
  };
  recent_users: OverviewLine[];
  recent_accounts: OverviewLine[];
  recent_logins: OverviewLine[];
}

const router = useRouter();
const OverviewUri = '/0x/system/admin-overview';
const loading = ref(false);

const overview = ref<OverviewPayload>({
  today: '',
  users: {
    total: 0,
    active: 0,
    specific_pool: 0,
    expiring_soon: 0,
  },
  accounts: {
    total: 0,
    available: 0,
    healthy: 0,
    relay: 0,
    web_enabled: 0,
    api_enabled: 0,
  },
  pools: {
    total: 0,
    non_empty: 0,
    account_slots: 0,
    bound_users: 0,
  },
  plans: {
    total: 0,
    active: 0,
    web_enabled: 0,
    api_enabled: 0,
  },
  traffic: {
    today_requests: 0,
    today_failed_requests: 0,
    today_total_tokens: 0,
    today_estimated_cost: 0,
    today_unique_users: 0,
    today_dispatch_empty: 0,
    top_models: [],
  },
  sync: {
    synced_user_count: 0,
    today_request_snapshot: 0,
    latest_sync_at: 0,
    today_login_count: 0,
    today_dispatch_selected: 0,
  },
  recent_users: [],
  recent_accounts: [],
  recent_logins: [],
});

const heroMetrics = computed(() => [
  {
    label: '可用用户',
    value: overview.value.users.active,
    meta: `${overview.value.users.total} 个总账户`,
    icon: NotificationIcon,
    color: '#0f766e',
  },
  {
    label: '可调度账号',
    value: overview.value.accounts.available,
    meta: `${overview.value.accounts.total} 个上游账号源`,
    icon: DataDisplayIcon,
    color: '#1d4ed8',
  },
  {
    label: '今日请求',
    value: overview.value.traffic.today_requests,
    meta: `${overview.value.traffic.today_total_tokens} tokens`,
    icon: ChartIcon,
    color: '#7c3aed',
  },
  {
    label: '今日成本',
    value: `$${Number(overview.value.traffic.today_estimated_cost || 0).toFixed(4)}`,
    meta: `${overview.value.traffic.today_failed_requests} 个失败请求`,
    icon: MoneyIcon,
    color: '#c2410c',
  },
]);

const loadOverview = async () => {
  loading.value = true;
  const response = await RequestApi(OverviewUri);
  if (response.ok) {
    overview.value = await response.json();
  }
  loading.value = false;
};

const formatTimestamp = (value?: number) => {
  if (!value) return '暂无';
  return TimestampToDate(value * 1000);
};

const formatDateTime = (value?: string) => {
  if (!value) return '暂无';
  return dayjs(value).format('YYYY-MM-DD HH:mm');
};

onMounted(async () => {
  await loadOverview();
});
</script>
