<template>
  <div class="ops-page">
    <admin-page-intro
      eyebrow="Upstream Accounts"
      title="上游账号"
      description="维护官方账号和中转站资源，控制可用状态、调度优先级和 Web/API 开关。"
    />

    <admin-metric-grid :items="metricCards" />

    <t-card class="list-card-container">
      <div class="ops-surface__head">
        <div>
          <h3>账号源列表</h3>
          <p>在同一张表里核对授权状态、健康状态和支持模型。</p>
        </div>
        <span class="ops-surface__badge">共 {{ pagination.total }} 个账号源</span>
      </div>

      <div class="ops-filter-bar">
        <div class="ops-filter-grid">
          <t-input v-model="filters.search" clearable placeholder="搜索账号标识或类型" style="width: 220px" />
          <t-select v-model="filters.account_type" clearable placeholder="接入方式" style="width: 150px">
            <t-option label="官方 Token" value="chatgpt_token" />
            <t-option label="中转站" value="relay_api" />
          </t-select>
          <t-select v-model="filters.source_type" clearable placeholder="来源" style="width: 140px">
            <t-option label="官方账号" value="official" />
            <t-option label="中转站" value="relay" />
          </t-select>
          <t-select v-model="filters.health_status" clearable placeholder="健康状态" style="width: 150px">
            <t-option label="健康" value="healthy" />
            <t-option label="降级" value="degraded" />
            <t-option label="停用" value="down" />
          </t-select>
          <t-select v-model="filters.auth_status" clearable placeholder="授权状态" style="width: 140px">
            <t-option label="可用" value="true" />
            <t-option label="失效" value="false" />
          </t-select>
          <t-select v-model="filters.enabled_for_web" clearable placeholder="网页可用" style="width: 140px">
            <t-option label="是" value="true" />
            <t-option label="否" value="false" />
          </t-select>
        </div>

        <div class="ops-filter-actions">
          <t-button theme="primary" @click="handleSearch">查询</t-button>
          <t-button theme="default" variant="outline" @click="handleReset">重置</t-button>
        </div>
      </div>

      <t-row justify="space-between">
        <div class="left-operation-container">
          <t-button @click="handleShowDialog">录入</t-button>

          <p v-if="!!selectedRowKeys.length" class="selected-count">
            {{ $t('pages.listBase.select') }} {{ selectedRowKeys.length }} {{ $t('pages.listBase.items') }}
          </p>
        </div>
      </t-row>
      <t-table
        :data="tableData"
        :columns="columns"
        row-key="chatgpt_username"
        :loading="tableLoading"
        :selected-row-keys="selectedRowKeys"
        bordered
        hover
        :pagination="pagination"
        @select-change="onSelectChange"
        @page-change="rehandlePageChange"
      >
        <template #auth_status="{ row }">
          <t-tag v-if="row.auth_status === false" theme="danger" variant="light"> 已过期 </t-tag>
          <t-tag v-if="row.auth_status === true" theme="success" variant="light"> 运行中 </t-tag>
        </template>

        <template #account_type="{ row }">
          <t-tag v-if="row.account_type === 'relay_api'" theme="warning" variant="light"> 中转站 </t-tag>
          <t-tag v-else theme="primary" variant="light"> ChatGPT </t-tag>
        </template>

        <template #source_type="{ row }">
          <t-tag v-if="row.source_type === 'relay'" theme="warning" variant="light"> 中转站 </t-tag>
          <t-tag v-else theme="primary" variant="light"> 官方账号 </t-tag>
        </template>

        <template #auth_mode="{ row }">
          {{ formatAuthMode(row.auth_mode) }}
        </template>

        <template #health_status="{ row }">
          <t-tag v-if="row.health_status === 'down'" theme="danger" variant="light"> 停用 </t-tag>
          <t-tag v-else-if="row.health_status === 'degraded'" theme="warning" variant="light"> 降级 </t-tag>
          <t-tag v-else theme="success" variant="light"> 健康 </t-tag>
        </template>

        <template #supported_models="{ row }">
          {{ row.supported_models?.length ? row.supported_models.join(', ') : '自动/不限' }}
        </template>

        <template #enabled_for_web="{ row }">
          {{ row.enabled_for_web ? '是' : '否' }}
        </template>

        <template #enabled_for_api="{ row }">
          {{ row.enabled_for_api ? '是' : '否' }}
        </template>

        <!--
        <template #use_count="{ row }">
          <t-space>
            <div v-for="(v, k) in row.use_count" :key="k">
              <t-tag v-if="k.toString().includes('h')">
                <t-space>
                  <span style="color: #0052c1">{{ k.toString().substring(5, 7) }}:</span>
                  <span>{{ v }}</span>
                </t-space>
              </t-tag>
            </div>
          </t-space>
        </template>
        -->

        <template #expires_at="{ row }">
          {{ TimestampToDate(row.expires_at) }}
        </template>

        <template #updated_at="{ row }">
          {{ TimestampToDate(row.updated_at) }}
        </template>

        <template #access_token_exp="{ row }">
          {{ row.access_token_exp ? TimestampToDate(row.access_token_exp * 1000) : '-' }}
        </template>

        <template #created_time="{ row }">
          {{ TimestampToDate(row.created_time * 1000) }}
        </template>

        <template #op="slotProps">
          <t-space>
            <!-- <t-link theme="primary" @click="handleUpdate(slotProps.row)">更新</t-link> -->
            <t-link theme="primary" @click="handleEdit(slotProps.row)">编辑</t-link>

            <t-link theme="danger" @click="handleClickDelete(slotProps.row)">删除</t-link>
          </t-space>
        </template>
      </t-table>

      <!-- 录入 Token dialog -->
      <t-dialog v-model:visible="showDialog" header="录入账号" width="50%" :on-confirm="handleAdd">
        <t-form v-loading="loading" :data="newChat" :label-width="100">
          <t-form-item label="接入方式">
            <t-radio-group v-model="newChat.account_type">
              <t-radio-button value="chatgpt_token">ChatGPT Token</t-radio-button>
              <t-radio-button value="relay_api">中转站 URL + Key</t-radio-button>
            </t-radio-group>
          </t-form-item>

          <template v-if="newChat.account_type === 'chatgpt_token'">
            <t-form-item label="Token">
              <div style="display: flex; flex-direction: column; width: 100%">
                <t-textarea
                  v-model="newChat.chatgpt_token"
                  :autosize="{ minRows: 5, maxRows: 5 }"
                  autofocus
                  size="large"
                  placeholder="请输入 Access Token 或 Session Token 或 Refresh Token。一行一串 Token，多个 Token 请换行输入。"
                ></t-textarea>
                <span style="font-size: 12px; color: #888">
                  <t-link target="_blank" theme="primary" size="small" href="https://chatgpt.com/api/auth/session">
                    Access Token</t-link
                  >：有效期10天
                </span>
                <span style="font-size: 12px; color: #888">
                  <t-link target="_blank" theme="primary" size="small" :href="ChatgptTokenTutorialUrl"
                    >Session Token</t-link
                  >：有效期30天
                </span>
                <span style="font-size: 12px; color: #888"> Refresh Token：有效期永久 </span>
              </div>
            </t-form-item>
          </template>

          <template v-else>
            <t-form-item label="账号标识">
              <t-input v-model="newChat.chatgpt_username" size="large" placeholder="例如：openai-relay-prod"></t-input>
            </t-form-item>
            <t-form-item label="中转站 URL">
              <t-input
                v-model="newChat.relay_base_url"
                size="large"
                placeholder="例如：https://relay.example.com 或 https://relay.example.com/v1"
              ></t-input>
            </t-form-item>
            <t-form-item label="API Key">
              <t-input v-model="newChat.relay_api_key" size="large" placeholder="请输入中转站 API Key"></t-input>
            </t-form-item>
            <t-form-item label="类型标记">
              <t-input v-model="newChat.plan_type" size="large" placeholder="默认 relay"></t-input>
            </t-form-item>
            <t-form-item label="备注">
              <t-input v-model="newChat.remark" size="large" placeholder="可选备注"></t-input>
            </t-form-item>
          </template>

          <t-form-item label="支持模型">
            <t-select v-model="newChat.supported_models" multiple filterable placeholder="留空表示自动/不限">
              <t-option v-for="item in modelOptions" :key="item" :label="item" :value="item" />
            </t-select>
          </t-form-item>
          <t-form-item label="优先级">
            <t-input-number v-model="newChat.priority" theme="normal" :min="0" />
          </t-form-item>
          <t-form-item label="权重">
            <t-input-number v-model="newChat.weight" theme="normal" :min="1" />
          </t-form-item>
          <t-form-item label="健康状态">
            <t-select v-model="newChat.health_status">
              <t-option v-for="item in healthStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </t-select>
          </t-form-item>
          <t-form-item label="网页可用">
            <t-switch v-model="newChat.enabled_for_web" :custom-value="[true, false]" />
          </t-form-item>
          <t-form-item label="API 可用">
            <t-switch v-model="newChat.enabled_for_api" :custom-value="[true, false]" />
          </t-form-item>
          <t-form-item label="最大并发">
            <t-input-number v-model="newChat.max_concurrency" theme="normal" :min="1" />
          </t-form-item>
          <t-form-item label="RPM">
            <t-input-number v-model="newChat.rpm_limit" theme="normal" :min="0" />
          </t-form-item>
          <t-form-item label="TPM">
            <t-input-number v-model="newChat.tpm_limit" theme="normal" :min="0" />
          </t-form-item>
          <t-form-item label="单位成本">
            <t-input-number v-model="newChat.unit_cost" theme="normal" :min="0" :step="0.0001" />
          </t-form-item>
        </t-form>
      </t-dialog>

      <!-- 编辑 备注信息 -->
      <t-dialog v-model:visible="dialogVisibleEdit" header="编辑信息" width="50%" :on-confirm="handleEditConfirm">
        <t-form v-loading="loading" :data="editChatInfo" :label-width="120">
          <t-form-item label="类型标记">
            <t-input v-model="editChatInfo.plan_type" size="large" placeholder="类型标记"></t-input>
          </t-form-item>
          <t-form-item label="备注信息">
            <t-input v-model="editChatInfo.remark" size="large" placeholder="备注信息"></t-input>
          </t-form-item>
          <t-form-item label="支持模型">
            <t-select v-model="editChatInfo.supported_models" multiple filterable placeholder="留空表示自动/不限">
              <t-option v-for="item in modelOptions" :key="item" :label="item" :value="item" />
            </t-select>
          </t-form-item>
          <t-form-item label="优先级">
            <t-input-number v-model="editChatInfo.priority" theme="normal" :min="0" />
          </t-form-item>
          <t-form-item label="权重">
            <t-input-number v-model="editChatInfo.weight" theme="normal" :min="1" />
          </t-form-item>
          <t-form-item label="健康状态">
            <t-select v-model="editChatInfo.health_status">
              <t-option v-for="item in healthStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </t-select>
          </t-form-item>
          <t-form-item label="网页可用">
            <t-switch v-model="editChatInfo.enabled_for_web" :custom-value="[true, false]" />
          </t-form-item>
          <t-form-item label="API 可用">
            <t-switch v-model="editChatInfo.enabled_for_api" :custom-value="[true, false]" />
          </t-form-item>
          <t-form-item label="最大并发">
            <t-input-number v-model="editChatInfo.max_concurrency" theme="normal" :min="1" />
          </t-form-item>
          <t-form-item label="RPM">
            <t-input-number v-model="editChatInfo.rpm_limit" theme="normal" :min="0" />
          </t-form-item>
          <t-form-item label="TPM">
            <t-input-number v-model="editChatInfo.tpm_limit" theme="normal" :min="0" />
          </t-form-item>
          <t-form-item label="单位成本">
            <t-input-number v-model="editChatInfo.unit_cost" theme="normal" :min="0" :step="0.0001" />
          </t-form-item>
        </t-form>
      </t-dialog>

      <!-- 确认删除 dialog -->
      <t-dialog
        v-model:visible="dialogVisibleDelete"
        header="确认删除该 ChatGPT token 吗"
        width="600"
        :on-confirm="handleDelete"
      >
      </t-dialog>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { AnalyticsIcon, ApiIcon, DataDisplayIcon, InternetIcon } from 'tdesign-icons-vue-next';
import { MessagePlugin, TableProps } from 'tdesign-vue-next';
import { computed, onMounted, reactive, ref } from 'vue';

import RequestApi from '@/api/request';
import AdminMetricGrid from '@/components/admin/AdminMetricGrid.vue';
import AdminPageIntro from '@/components/admin/AdminPageIntro.vue';
import { ChatgptTokenTutorialUrl } from '@/constants/index';
import { TimestampToDate } from '@/utils/date';

interface TableData {
  chatgpt_username: string;
  account_type: string;
  source_type: string;
  auth_mode: string;
  auth_status: boolean;
  health_status: string;
  plan_type: string;
  supported_models: string[];
  enabled_for_web: boolean;
  enabled_for_api: boolean;
  priority: number;
  weight: number;
  max_concurrency: number;
  rpm_limit: number;
  tpm_limit: number;
  unit_cost: number;
  access_token_exp: number;
  remark: string;
}
const selectedRowKeys = ref<TableProps['selectedRowKeys']>([]);
const loading = ref(false);
const tableLoading = ref(false);
const tableData = ref<TableData[]>([]);
const filters = reactive({
  search: '',
  account_type: '',
  health_status: '',
  source_type: '',
  auth_status: '',
  enabled_for_web: '',
});

const pagination = {
  defaultPageSize: 20,
  total: 0,
  defaultCurrent: 1,
};

const rehandlePageChange = (curr: any) => {
  pagination.defaultCurrent = curr.current;
  pagination.defaultPageSize = curr.pageSize;
  getChatGPTList();
};

const columns: TableProps['columns'] = [
  { colKey: 'row-select', type: 'multiple' },
  { colKey: 'id', title: 'ID', width: 50 },
  { colKey: 'chatgpt_username', title: '账号标识', width: 220, fixed: 'left' },
  { colKey: 'account_type', title: '接入方式', width: 120 },
  { colKey: 'source_type', title: '来源', width: 100 },
  { colKey: 'auth_mode', title: '授权方式', width: 120 },
  { colKey: 'auth_status', title: '状态', width: 100, fixed: 'left' },
  { colKey: 'health_status', title: '健康状态', width: 100 },
  { colKey: 'plan_type', title: '类型', width: 100 },
  { colKey: 'supported_models', title: '支持模型', width: 220 },
  { colKey: 'enabled_for_web', title: '网页', width: 70 },
  { colKey: 'enabled_for_api', title: 'API', width: 70 },
  { colKey: 'priority', title: '优先级', width: 90 },
  { colKey: 'weight', title: '权重', width: 70 },
  { colKey: 'max_concurrency', title: '并发', width: 80 },
  { colKey: 'rpm_limit', title: 'RPM', width: 80 },
  { colKey: 'tpm_limit', title: 'TPM', width: 90 },
  { colKey: 'unit_cost', title: '成本', width: 90 },
  // { colKey: 'use_count', title: '近期用量', width: 350 },
  { colKey: 'access_token_exp', title: 'Access Token 过期时间', width: 200 },
  { colKey: 'created_time', title: '创建时间', width: 200 },
  // { colKey: 'updated_at', title: '最近更新时间', width: 200 },
  { colKey: 'remark', title: '备注' },
  { width: 200, colKey: 'op', title: '操作' },
];

const metricCards = computed(() => {
  const healthyCount = tableData.value.filter((item) => item.health_status === 'healthy' && item.auth_status).length;
  const relayCount = tableData.value.filter((item) => item.account_type === 'relay_api').length;
  const webEnabledCount = tableData.value.filter((item) => item.enabled_for_web).length;
  return [
    {
      label: '账号源总数',
      value: pagination.total,
      meta: '官方账号与中转账号统一管理',
      icon: DataDisplayIcon,
      color: '#1d4ed8',
    },
    {
      label: '当前页健康',
      value: healthyCount,
      meta: '授权有效且健康状态正常',
      icon: AnalyticsIcon,
      color: '#0f766e',
    },
    {
      label: '中转账号',
      value: relayCount,
      meta: '当前页 relay 资源数量',
      icon: InternetIcon,
      color: '#7c3aed',
    },
    {
      label: '网页可用',
      value: webEnabledCount,
      meta: '允许 Web 侧直接调度',
      icon: ApiIcon,
      color: '#c2410c',
    },
  ];
});
const showDialog = ref(false);
const dialogVisibleDelete = ref(false);
const usernameDelete = ref('');
const dialogVisibleEdit = ref(false);

const createNewChatForm = () => ({
  account_type: 'chatgpt_token',
  chatgpt_token: '',
  chatgpt_username: '',
  relay_base_url: '',
  relay_api_key: '',
  plan_type: '',
  remark: '',
  supported_models: [] as string[],
  priority: 100,
  weight: 1,
  health_status: 'healthy',
  max_concurrency: 1,
  rpm_limit: 0,
  tpm_limit: 0,
  unit_cost: 0,
  enabled_for_web: true,
  enabled_for_api: true,
});
const newChat = ref(createNewChatForm());
const editChatInfo = ref({
  chatgpt_username: '',
  plan_type: '',
  remark: '',
  supported_models: [] as string[],
  priority: 100,
  weight: 1,
  health_status: 'healthy',
  max_concurrency: 1,
  rpm_limit: 0,
  tpm_limit: 0,
  unit_cost: 0,
  enabled_for_web: true,
  enabled_for_api: true,
});
const modelOptions = [
  'gpt-5.4',
  'gpt-5.3-codex',
  'gpt-5.2',
  'gpt-4',
  'gpt-4o',
  'gpt-4o-mini',
  'o1',
  'o1-mini',
  'o1-pro',
  'claude-3-5-sonnet',
];
const healthStatusOptions = [
  { label: '健康', value: 'healthy' },
  { label: '降级', value: 'degraded' },
  { label: '停用', value: 'down' },
];

const ChatgptTokenUrl = '/0x/chatgpt/';

onMounted(async () => {
  await getChatGPTList();
});

const getChatGPTList = async () => {
  // 发送请求获取 Token 列表
  tableLoading.value = true;
  const params: any = {
    page: pagination.defaultCurrent,
    page_size: pagination.defaultPageSize,
  };
  if (filters.search) params.search = filters.search;
  if (filters.account_type) params.account_type = filters.account_type;
  if (filters.health_status) params.health_status = filters.health_status;
  if (filters.source_type) params.source_type = filters.source_type;
  if (filters.auth_status) params.auth_status = filters.auth_status;
  if (filters.enabled_for_web) params.enabled_for_web = filters.enabled_for_web;

  const queryString = new URLSearchParams(params).toString();
  const response = await RequestApi(`${ChatgptTokenUrl}?${queryString}`);

  const data = await response.json();
  // console.log('results', data.results);
  tableData.value = data.results;
  pagination.total = data.count;

  tableLoading.value = false;
};

const handleSearch = async () => {
  pagination.defaultCurrent = 1;
  await getChatGPTList();
};

const handleReset = async () => {
  filters.search = '';
  filters.account_type = '';
  filters.health_status = '';
  filters.source_type = '';
  filters.auth_status = '';
  filters.enabled_for_web = '';
  pagination.defaultCurrent = 1;
  await getChatGPTList();
};

const addChatToken = async () => {
  // 发送请求添加 Token
  loading.value = true;
  const payload =
    newChat.value.account_type === 'relay_api'
      ? {
          account_type: newChat.value.account_type,
          chatgpt_username: newChat.value.chatgpt_username.trim(),
          relay_base_url: newChat.value.relay_base_url.trim(),
          relay_api_key: newChat.value.relay_api_key.trim(),
          plan_type: newChat.value.plan_type.trim() || 'relay',
          remark: newChat.value.remark.trim(),
          supported_models: newChat.value.supported_models,
          priority: newChat.value.priority,
          weight: newChat.value.weight,
          health_status: newChat.value.health_status,
          max_concurrency: newChat.value.max_concurrency,
          rpm_limit: newChat.value.rpm_limit,
          tpm_limit: newChat.value.tpm_limit,
          unit_cost: newChat.value.unit_cost,
          enabled_for_web: newChat.value.enabled_for_web,
          enabled_for_api: newChat.value.enabled_for_api,
        }
      : {
          account_type: newChat.value.account_type,
          chatgpt_token_list: newChat.value.chatgpt_token.split('\n'),
          plan_type: newChat.value.plan_type.trim(),
          remark: newChat.value.remark.trim(),
          supported_models: newChat.value.supported_models,
          priority: newChat.value.priority,
          weight: newChat.value.weight,
          health_status: newChat.value.health_status,
          max_concurrency: newChat.value.max_concurrency,
          rpm_limit: newChat.value.rpm_limit,
          tpm_limit: newChat.value.tpm_limit,
          unit_cost: newChat.value.unit_cost,
          enabled_for_web: newChat.value.enabled_for_web,
          enabled_for_api: newChat.value.enabled_for_api,
        };

  const response = await RequestApi(ChatgptTokenUrl, 'POST', payload);

  const data = await response.json();
  loading.value = false;

  if (response.status !== 200) {
    MessagePlugin.error(JSON.stringify(Object.values(data)[0]));

    // if (data.message.includes('status: 403')) {
    //   window.location.href = '/';
    // }
  } else {
    showDialog.value = false;
    await getChatGPTList();
    newChat.value = createNewChatForm();
    MessagePlugin.success('新增成功');
  }
};

const formatAuthMode = (authMode: string) => {
  const authModeMap: Record<string, string> = {
    access_token: 'Access Token',
    session_token: 'Session Token',
    refresh_token: 'Refresh Token',
    relay_url_key: 'URL + Key',
  };
  return authModeMap[authMode] || authMode || '-';
};

const handleEdit = (row: any) => {
  editChatInfo.value = {
    chatgpt_username: row.chatgpt_username,
    plan_type: row.plan_type || '',
    remark: row.remark || '',
    supported_models: row.supported_models || [],
    priority: row.priority ?? 100,
    weight: row.weight ?? 1,
    health_status: row.health_status || 'healthy',
    max_concurrency: row.max_concurrency ?? 1,
    rpm_limit: row.rpm_limit ?? 0,
    tpm_limit: row.tpm_limit ?? 0,
    unit_cost: Number(row.unit_cost ?? 0),
    enabled_for_web: row.enabled_for_web ?? true,
    enabled_for_api: row.enabled_for_api ?? true,
  };
  dialogVisibleEdit.value = true;
};

const handleShowDialog = () => {
  newChat.value = createNewChatForm();
  showDialog.value = true;
};

const handleClickDelete = (row: any) => {
  usernameDelete.value = row.chatgpt_username;
  dialogVisibleDelete.value = true;
};

const handleDelete = async () => {
  const response = await RequestApi(ChatgptTokenUrl, 'DELETE', { chatgpt_username: usernameDelete.value });

  const data = await response.json();
  dialogVisibleDelete.value = false;
  usernameDelete.value = '';

  if (response.status !== 200) {
    MessagePlugin.error(JSON.stringify(Object.values(data)[0]));
  } else {
    await getChatGPTList();
    MessagePlugin.success('删除成功');
  }
};

const handleAdd = () => {
  if (newChat.value.account_type === 'relay_api' && newChat.value.chatgpt_username.trim() === '') {
    MessagePlugin.error('账号标识不能为空');
  } else if (newChat.value.account_type === 'relay_api' && newChat.value.relay_base_url.trim() === '') {
    MessagePlugin.error('中转站 URL 不能为空');
  } else if (newChat.value.account_type === 'relay_api' && newChat.value.relay_api_key.trim() === '') {
    MessagePlugin.error('中转站 Key 不能为空');
  } else if (newChat.value.account_type === 'chatgpt_token' && newChat.value.chatgpt_token.trim() === '') {
    MessagePlugin.error('Token 不能为空');
  } else {
    addChatToken();
  }
};

const onSelectChange: TableProps['onSelectChange'] = (value, _) => {
  selectedRowKeys.value = value;
  // console.log(value, ctx);
};

const handleEditConfirm = async () => {
  await RequestApi(ChatgptTokenUrl, 'PUT', {
    plan_type: editChatInfo.value.plan_type,
    remark: editChatInfo.value.remark,
    chatgpt_username: editChatInfo.value.chatgpt_username,
    supported_models: editChatInfo.value.supported_models,
    priority: editChatInfo.value.priority,
    weight: editChatInfo.value.weight,
    health_status: editChatInfo.value.health_status,
    max_concurrency: editChatInfo.value.max_concurrency,
    rpm_limit: editChatInfo.value.rpm_limit,
    tpm_limit: editChatInfo.value.tpm_limit,
    unit_cost: editChatInfo.value.unit_cost,
    enabled_for_web: editChatInfo.value.enabled_for_web,
    enabled_for_api: editChatInfo.value.enabled_for_api,
  });
  await getChatGPTList();
  MessagePlugin.success('修改成功');
  dialogVisibleEdit.value = false;
};
</script>

<style lang="less" scoped>
.left-operation-container {
  padding: 6px 0;
  margin-bottom: 16px;

  .selected-count {
    display: inline-block;
    margin-left: 8px;
    color: var(--td-text-color-secondary);
  }
}
</style>
