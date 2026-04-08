<!-- eslint-disable camelcase -->
<template>
  <div class="ops-page">
    <admin-page-intro
      eyebrow="Users & Access"
      title="用户管理"
      description="统一维护站点登录账户、套餐绑定、号池策略和模型限制。"
    />

    <admin-metric-grid :items="metricCards" />

    <t-card class="list-card-container">
      <div class="ops-surface__head">
        <div>
          <h3>用户列表</h3>
          <p>按用户查看套餐、账号池模式、独立会话和最近登录情况。</p>
        </div>
        <span class="ops-surface__badge">共 {{ pagination.total }} 个用户</span>
      </div>

      <div class="ops-filter-bar">
        <div class="ops-filter-grid">
          <t-input v-model="filters.search" clearable placeholder="搜索用户名或邮箱" style="width: 220px" />
          <t-select v-model="filters.status" clearable placeholder="账户状态" style="width: 150px">
            <t-option label="正常" value="active" />
            <t-option label="停用" value="disabled" />
            <t-option label="过期" value="expired" />
          </t-select>
          <t-select v-model="filters.pool_mode" clearable placeholder="账号池模式" style="width: 160px">
            <t-option label="公共账号池" value="public_pool" />
            <t-option label="指定号池" value="specific_pools" />
          </t-select>
          <t-select v-model="filters.is_active" clearable placeholder="启用状态" style="width: 140px">
            <t-option label="启用" value="true" />
            <t-option label="停用" value="false" />
          </t-select>
          <t-select v-model="filters.plan_id" clearable placeholder="套餐" style="width: 180px">
            <t-option v-for="item in planList" :key="item.id" :label="item.name" :value="String(item.id)" />
          </t-select>
        </div>

        <div class="ops-filter-actions">
          <t-button theme="primary" @click="handleSearch">查询</t-button>
          <t-button theme="default" variant="outline" @click="handleReset">重置</t-button>
        </div>
      </div>

      <t-row justify="space-between">
        <div class="left-operation-container">
          <!-- <t-button @click="$router.push('/login')">访问</t-button> -->
          <t-button @click="handleShowDialog()">新增</t-button>
          <t-button
            variant="base"
            :loading="loading"
            theme="default"
            :disabled="!selectedRowKeys.length"
            @click="BatcModelLimit"
          >
            限制</t-button
          >
          <p v-if="!!selectedRowKeys.length" class="selected-count">
            {{ $t('pages.listBase.select') }} {{ selectedRowKeys.length }} {{ $t('pages.listBase.items') }}
          </p>
        </div>
      </t-row>
      <t-table
        :data="tableData"
        :columns="columns"
        row-key="id"
        :loading="tableLoading"
        bordered
        hover
        :pagination="pagination"
        @page-change="rehandlePageChange"
        @select-change="onSelectChange"
      >
        <template #is_active="{ row }">
          <t-switch :value="row.is_active" :custom-value="[true, false]">
            <!-- <template #label="slotProps">{{ slotProps.value == 1 ? '启用' : '停用' }} </template> -->
          </t-switch>
        </template>

        <template #title-username>
          <div><user-circle-icon style="margin-right: 8px" />用户</div>
        </template>

        <template #last_login="{ row }">
          {{ row.last_login }}
        </template>

        <template #chatgpt_count="{ row }">
          <t-link theme="primary" @click="getChatGPTDetails(row)">可用账号: {{ row.chatgpt_count }} 个</t-link>
        </template>

        <template #pool_mode="{ row }">
          <t-tag v-if="row.pool_mode === 'specific_pools'" theme="warning" variant="light">指定号池</t-tag>
          <t-tag v-else theme="success" variant="light">站点公共账号池</t-tag>
        </template>

        <template #isolated_session="{ row }">
          <t-switch :value="row.isolated_session" :custom-value="[true, false]">
            <!--             @change="(value) => changeIsolatedSession(row, Number(value))" -->
            <template #label="slotProps">{{ slotProps.value == true ? '是' : '否' }} </template>
          </t-switch>
        </template>

        <template #op="slotProps">
          <t-space>
            <t-link theme="primary" @click="handleEdit(slotProps.row)"> 编辑</t-link>
            <t-link theme="danger" @click="handleClickDelete(slotProps.row)"> 删除</t-link>
          </t-space>
        </template>
      </t-table>

      <!-- chatgpt 账号 -->
      <t-dialog
        v-model:visible="showChatGPTDetailsDialog"
        title="ChatGPT 账号详情"
        width="950px"
        :cancel-btn="null"
        :confirm-btn="null"
      >
        <user-chatgpt-details-component ref="userChatgptDetailsRef" />
      </t-dialog>

      <!-- 添加/编辑 用户 dialog -->
      <t-dialog v-model:visible="showDialog" :on-confirm="handleConfirm" title="新增 用户" width="800px">
        <t-form
          ref="addFormRef"
          v-loading="loading"
          :rules="rules"
          :data="newUser"
          :label-width="120"
          @submit="handleAdd"
        >
          <t-form-item label="状态" name="is_active">
            <t-radio-group v-model="newUser.is_active" class="side-mode-radio">
              <t-radio-button key="true" :value="true" label="启用" />
              <t-radio-button key="false" :value="false" label="停用" />
            </t-radio-group>
          </t-form-item>

          <t-form-item label="用户名" name="username">
            <t-input v-model="newUser.username" :disabled="actionType == 'edit'" style="width: 240px"></t-input>
          </t-form-item>

          <t-form-item label="邮箱" name="email">
            <t-input v-model="newUser.email" style="width: 240px"></t-input>
          </t-form-item>

          <t-form-item v-if="actionType == 'add'" label="密码" name="password">
            <t-input v-model="newUser.password" style="width: 240px"></t-input>
          </t-form-item>

          <t-form-item label="独立会话" name="isolated_session">
            <t-switch v-model="newUser.isolated_session" :custom-value="[true, false]" />
          </t-form-item>

          <t-form-item label="过期日期" name="expired_date">
            <t-date-picker
              v-model="newUser.expired_date"
              placeholder=""
              :disable-date="{
                before: dayjs().subtract(0, 'day').format(),
              }"
              clearable
              allow-input
            />
          </t-form-item>

          <t-form-item label="账号池" name="binding_gptcar_list">
            <t-space>
              <t-radio-group v-model="newUser.pool_mode" class="side-mode-radio">
                <t-radio-button key="public_pool" value="public_pool" label="站点公共账号池" />
                <t-radio-button key="specific_pools" value="specific_pools" label="指定号池" />
              </t-radio-group>

              <t-select
                v-if="newUser.pool_mode === 'specific_pools'"
                v-model="newUser.binding_gptcar_list"
                multiple
                placeholder="Select"
                filterable
                style="width: 240px"
              >
                <t-option v-for="item in gptCarList" :key="item.car_name" :label="item.car_name" :value="item.id" />
              </t-select>
            </t-space>
          </t-form-item>

          <t-form-item label="套餐" name="plan_id">
            <t-select v-model="newUser.plan_id" clearable style="width: 240px" placeholder="不选表示不限制套餐">
              <t-option v-for="item in planList" :key="item.id" :label="item.name" :value="item.id" />
            </t-select>
          </t-form-item>

          <t-form-item label="限制" name="model_limit">
            <t-space direction="vertical">
              <t-switch
                v-model="hasModelLimit"
                :custom-value="[true, false]"
                @change="(value) => onModelLimitChange(value as boolean)"
              />
              <div v-if="hasModelLimit">
                <t-space direction="vertical" :size="3">
                  <div v-for="(line, idx) in newUser.model_limit" :key="line">
                    <t-space :size="5" align="center">
                      <t-select v-model="line.model_name" filterable style="width: 120px">
                        <t-option
                          v-for="model in modelList"
                          :key="model.value"
                          :label="model.label"
                          :value="model.value"
                        />
                      </t-select>
                      <span>限制</span>
                      <t-input-adornment prepend="每" append="分钟">
                        <t-input-number v-model="line.every_minute" theme="normal" min="0" style="width: 70px" />
                      </t-input-adornment>
                      <span>发送</span>
                      <t-input-adornment append="条">
                        <t-input-number v-model="line.limit_count" theme="normal" min="0" style="width: 70px" />
                      </t-input-adornment>
                      <span>消息</span>

                      <div>
                        <t-button
                          v-if="idx + 1 === newUser.model_limit.length"
                          shape="circle"
                          theme="primary"
                          style="margin-left: 10px"
                          @click="onAddModelLimit()"
                        >
                          <template #icon><add-icon /></template>
                        </t-button>

                        <t-button
                          v-else
                          shape="circle"
                          theme="danger"
                          style="margin-left: 10px"
                          @click="onDeleteModelLimit(idx)"
                        >
                          <template #icon><delete-icon /></template>
                        </t-button>
                      </div>
                    </t-space>
                  </div>
                </t-space>
              </div>
            </t-space>
          </t-form-item>

          <t-form-item label="备注" name="remark">
            <t-textarea v-model="newUser.remark"></t-textarea>
          </t-form-item>
        </t-form>
      </t-dialog>

      <!--- 模型限制 dialog  -->
      <t-dialog
        v-model:visible="showModelLimitDialog"
        :on-confirm="handleBatchModelLimitConfirm"
        title="批量限制模型"
        width="800px"
      >
        <t-form
          ref="batchModelLimitUserFormRef"
          v-loading="loading"
          :data="batchModelLimitUser"
          :rules="rules"
          :label-width="120"
          @submit="handlebatchModelLimit"
        >
          <t-form-item label="限制" name="model_limit">
            <t-space direction="vertical">
              <t-switch
                v-model="hasModelLimit"
                :custom-value="[true, false]"
                @change="(value) => onModelLimitChange(value as boolean)"
              />
              <div v-if="hasModelLimit">
                <t-space direction="vertical" :size="3">
                  <div v-for="(line, idx) in batchModelLimitUser.model_limit" :key="line">
                    <t-space :size="5" align="center">
                      <t-select v-model="line.model_name" filterable style="width: 120px">
                        <t-option
                          v-for="model in modelList"
                          :key="model.value"
                          :label="model.label"
                          :value="model.value"
                        />
                      </t-select>
                      <span>限制</span>
                      <t-input-adornment prepend="每" append="分钟">
                        <t-input-number v-model="line.every_minute" theme="normal" min="0" style="width: 70px" />
                      </t-input-adornment>
                      <span>发送</span>
                      <t-input-adornment append="条">
                        <t-input-number v-model="line.limit_count" theme="normal" min="0" style="width: 70px" />
                      </t-input-adornment>
                      <span>消息</span>

                      <div>
                        <t-button
                          v-if="idx + 1 === batchModelLimitUser.model_limit.length"
                          shape="circle"
                          theme="primary"
                          style="margin-left: 10px"
                          @click="onAddModelLimit('batch')"
                        >
                          <template #icon><add-icon /></template>
                        </t-button>

                        <t-button
                          v-else
                          :disabled="batchModelLimitUser.username == 'free'"
                          shape="circle"
                          theme="danger"
                          style="margin-left: 10px"
                          @click="onDeleteModelLimit(idx, 'batch')"
                        >
                          <template #icon><delete-icon /></template>
                        </t-button>
                      </div>
                    </t-space>
                  </div>
                </t-space>
              </div>
            </t-space>
          </t-form-item>
        </t-form>
      </t-dialog>
      <!-- 确认删除 dialog -->
      <t-dialog v-model:visible="showDeleteDialog" header="确认删除该用户吗？" width="500" :on-confirm="handleDelete">
      </t-dialog>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import dayjs from 'dayjs';
import { AddIcon, AnalyticsIcon, DataDisplayIcon, DeleteIcon, SecuredIcon, UserCircleIcon, UsergroupIcon } from 'tdesign-icons-vue-next';
import { CustomValidator, FormProps, MessagePlugin, TableProps } from 'tdesign-vue-next';
import { computed, onMounted, reactive, ref } from 'vue';

import RequestApi from '@/api/request';
import AdminMetricGrid from '@/components/admin/AdminMetricGrid.vue';
import AdminPageIntro from '@/components/admin/AdminPageIntro.vue';

import UserChatgptDetailsComponent from './user_chatgpt.vue';

const userChatgptDetailsRef = ref<typeof UserChatgptDetailsComponent | null>(null);

interface TableData {
  token: string;
  user_info: string;
}

const hasModelLimit = ref(false);
const actionType = ref('add');
const loading = ref(false);
const tableLoading = ref(false);
const tableData = ref<TableData[]>([]);
const gptCarList = ref<any>([]);
const planList = ref<any[]>([]);
const showDialog = ref(false);
const showModelLimitDialog = ref(false);
const showDeleteDialog = ref(false);
const usernameDelete = ref('');
const addFormRef = ref();
const batchModelLimitUserFormRef = ref();
const UserAccountUri = '/0x/user/';
const BatchModelLimitUri = '/0x/user/batch-model-limit';
const GptCarEnumUri = '/0x/chatgpt/car-enum';
const PlanEnumUri = '/0x/plan/enum';
const selectedRowKeys = ref<TableProps['selectedRowKeys']>([]);
const showChatGPTDetailsDialog = ref(false);
const filters = reactive({
  search: '',
  status: '',
  pool_mode: '',
  is_active: '',
  plan_id: '',
});

interface TokenUserForm {
  is_active: boolean;
  status?: string;
  username: string;
  password?: string;
  email?: string;
  email_verified?: boolean;
  chatgpt_username: string;
  isolated_session: boolean;
  remark: string;
  model_limit: any[];
  pool_mode: string;
  binding_gptcar_list: any[];
  gptcar_list: any[];
  quota_snapshot?: Record<string, any>;
  plan_id?: number | null;
  expired_date: any;
}

const pagination = {
  defaultPageSize: 20,
  total: 0,
  defaultCurrent: 1,
};

const rehandlePageChange = (curr: any) => {
  pagination.defaultCurrent = curr.current;
  pagination.defaultPageSize = curr.pageSize;
  getUserList();
};

const BatcModelLimit = async () => {
  showModelLimitDialog.value = true;
};
const onSelectChange: TableProps['onSelectChange'] = (value, _) => {
  selectedRowKeys.value = value;
  // console.log(value, _);
};

const columns: TableProps['columns'] = [
  { colKey: 'row-select', type: 'multiple', checkProps: ({ row }) => ({ disabled: row.username === 'free_account' }) },
  { colKey: 'is_active', title: '状态', width: 100 },
  { colKey: 'username', title: 'title-username', width: 200, fixed: 'left' },
  { colKey: 'email', title: '邮箱', width: 220 },
  { colKey: 'plan_name', title: '套餐', width: 140 },
  { colKey: 'pool_mode', title: '账号池模式', width: 140 },
  { colKey: 'isolated_session', title: '独立会话', width: 100 },
  { colKey: 'chatgpt_count', title: 'ChatGPT', width: 120 },
  { colKey: 'use_count', title: '当日用量', width: 100 },
  { colKey: 'last_login', title: '最近登录时间', width: 160 },
  { colKey: 'expired_date', title: '过期日期', width: 160 },
  { colKey: 'date_joined', title: '注册时间', width: 160 },
  { colKey: 'remark', title: '备注', width: 200 },
  { width: 200, colKey: 'op', title: '操作' },
];

const metricCards = computed(() => {
  const activeCount = tableData.value.filter((item: any) => item.is_active && item.status !== 'disabled').length;
  const isolatedCount = tableData.value.filter((item: any) => item.isolated_session).length;
  const specificPoolCount = tableData.value.filter((item: any) => item.pool_mode === 'specific_pools').length;
  return [
    {
      label: '用户总数',
      value: pagination.total,
      meta: '后台当前可管理的登录账户',
      icon: UsergroupIcon,
      color: '#1d4ed8',
    },
    {
      label: '当前页启用',
      value: activeCount,
      meta: '本页状态正常的用户',
      icon: SecuredIcon,
      color: '#0f766e',
    },
    {
      label: '指定号池',
      value: specificPoolCount,
      meta: '当前页使用专属资源池的用户',
      icon: DataDisplayIcon,
      color: '#7c3aed',
    },
    {
      label: '独立会话',
      value: isolatedCount,
      meta: `${selectedRowKeys.value.length} 个用户已选中`,
      icon: AnalyticsIcon,
      color: '#c2410c',
    },
  ];
});

const modelLimitValidator: CustomValidator = (val) => {
  for (const item of val) {
    if (!item.model_name) {
      return { result: false, message: '模型不能为空', type: 'error' };
    }
    if (!item.every_minute || item.every_minute <= 0) {
      return { result: false, message: '每分钟限制必须大于0', type: 'error' };
    }
    if (!item.limit_count || item.limit_count <= 0) {
      return { result: false, message: '发送条数必须大于0', type: 'error' };
    }
  }

  return { result: true, message: '', type: 'success' };
};

const rules: FormProps['rules'] = {
  // gptcar_list: [{ required: true, message: 'Please input gptcar_list', trigger: 'blur' }],
  model_limit: [{ validator: modelLimitValidator, trigger: 'change' }],
  is_active: [{ required: true, message: 'Please input is_active', trigger: 'blur' }],
  username: [
    { required: true, message: 'Please input username', trigger: 'blur' },
    { validator: (val) => val.length >= 4, message: '至少 4 个字符' },
  ],
  password: [{ required: true, message: 'Please input password', trigger: 'blur' }],
  isolated_session: [{ required: true, message: 'Please select isolated_session', trigger: 'blur' }],
};

const modelList = [
  { label: 'GPT-5.4', value: 'gpt-5.4' },
  { label: 'GPT-5.3 Codex', value: 'gpt-5.3-codex' },
  { label: 'GPT-5.2', value: 'gpt-5.2' },
  { label: 'GPT-4', value: 'gpt-4' },
  { label: 'GPT-4o', value: 'gpt-4o' },
  { label: 'GPT-4o-mini', value: 'gpt-4o-mini' },
  { label: 'o1-mini', value: 'o1-mini' },
  { label: 'o1', value: 'o1' },
  { label: 'o1-pro', value: 'o1-pro' },

];

const defaultUser = {
  is_active: true,
  status: 'active',
  username: '',
  password: '',
  email: '',
  email_verified: false,
  chatgpt_username: '',
  isolated_session: false,
  remark: '',
  model_limit: [] as any[],
  pool_mode: 'public_pool',
  binding_gptcar_list: [] as any[],
  gptcar_list: [] as any[],
  quota_snapshot: {} as Record<string, any>,
  plan_id: null as number | null,
  expired_date: undefined as Date | undefined,
};

const batchModelLimitUser = ref(JSON.parse(JSON.stringify({ model_limit: defaultUser.model_limit })));

const newUser = ref<TokenUserForm>({ ...defaultUser });

const getGptCarEnum = async () => {
  // 发送请求获取 号池 列表
  const response = await RequestApi(GptCarEnumUri);
  const data = await response.json();
  gptCarList.value = data.data;
};

const getPlanEnum = async () => {
  const response = await RequestApi(PlanEnumUri);
  const data = await response.json();
  planList.value = data.data || [];
};

const onAddModelLimit = (atype = 'default') => {
  if (atype === 'default') {
    newUser.value.model_limit.push({});
  } else {
    batchModelLimitUser.value.model_limit.push({});
  }
};
const onDeleteModelLimit = (idx: number, atype: string = 'default') => {
  if (atype === 'default') {
    newUser.value.model_limit.splice(idx, 1);
  } else {
    batchModelLimitUser.value.model_limit.splice(idx, 1);
  }
};

const getUserList = async () => {
  // 发送请求获取 用户 列表
  tableLoading.value = true;

  const params: any = {
    page: pagination.defaultCurrent,
    page_size: pagination.defaultPageSize,
  };
  if (filters.search) params.search = filters.search;
  if (filters.status) params.status = filters.status;
  if (filters.pool_mode) params.pool_mode = filters.pool_mode;
  if (filters.is_active) params.is_active = filters.is_active;
  if (filters.plan_id) params.plan_id = filters.plan_id;

  const queryString = new URLSearchParams(params).toString();
  const response = await RequestApi(`${UserAccountUri}?${queryString}`);

  const data = await response.json();
  tableData.value = data.results;
  pagination.total = data.count;
  tableLoading.value = false;
};

const handleSearch = async () => {
  pagination.defaultCurrent = 1;
  await getUserList();
};

const handleReset = async () => {
  filters.search = '';
  filters.status = '';
  filters.pool_mode = '';
  filters.is_active = '';
  filters.plan_id = '';
  pagination.defaultCurrent = 1;
  await getUserList();
};

const handleConfirm = async () => {
  if (addFormRef.value) {
    addFormRef.value.submit();
  }
};

const handleBatchModelLimitConfirm = async () => {
  if (batchModelLimitUserFormRef.value) {
    batchModelLimitUserFormRef.value.submit();
  }
};

const addOrUpdateUser = async () => {
  // 发送请求 添加/编辑 用户

  loading.value = true;
  if (newUser.value.pool_mode === 'public_pool') {
    newUser.value.binding_gptcar_list = [];
    newUser.value.gptcar_list = [];
  } else {
    newUser.value.gptcar_list = [...newUser.value.binding_gptcar_list];
  }

  newUser.value.expired_date = newUser.value.expired_date || null;
  const response = await RequestApi(UserAccountUri, 'POST', newUser.value);

  const data = await response.json();
  loading.value = false;

  if (response.status !== 200) {
    MessagePlugin.error(JSON.stringify(Object.values(data)[0]));
  } else {
    await getUserList();
    newUser.value = defaultUser;
    showDialog.value = false;
    MessagePlugin.success('新增成功');
  }
};

const batchUpdateUserModelLimit = async () => {
  //  批量更新 用户模型限制
  console.log(selectedRowKeys, batchModelLimitUser.value);
  loading.value = true;
  const response = await RequestApi(BatchModelLimitUri, 'POST', {
    model_limit: batchModelLimitUser.value.model_limit,
    user_id_list: selectedRowKeys.value,
  });

  const data = await response.json();
  loading.value = false;

  if (response.status !== 200) {
    MessagePlugin.error(JSON.stringify(Object.values(data)[0]));
  } else {
    await getUserList();
    batchModelLimitUser.value = JSON.parse(JSON.stringify({ model_limit: defaultUser.model_limit }));
    showModelLimitDialog.value = false;
    MessagePlugin.success('限制成功');
  }
};

const handleEdit = async (user: TokenUserForm) => {
  newUser.value = { ...user };
  hasModelLimit.value = Boolean(newUser.value.model_limit.length !== 0);
  newUser.value.binding_gptcar_list = [...(user.binding_gptcar_list || user.gptcar_list || [])];
  newUser.value.pool_mode = user.pool_mode || (newUser.value.binding_gptcar_list.length ? 'specific_pools' : 'public_pool');

  await getGptCarEnum();
  await getPlanEnum();

  showDialog.value = true;
  actionType.value = 'edit';
};

const handleShowDialog = async () => {
  await getGptCarEnum();
  await getPlanEnum();
  showDialog.value = true;
  actionType.value = 'add';
  newUser.value = { ...defaultUser };
};

const handleClickDelete = (row: any) => {
  console.log('row', row.username);
  usernameDelete.value = row.username;
  showDeleteDialog.value = true;
};

const handleDelete = async () => {
  const response = await RequestApi(UserAccountUri, 'DELETE', { username: usernameDelete.value });
  const data = await response.json();
  showDeleteDialog.value = false;
  usernameDelete.value = '';

  if (response.status !== 200) {
    MessagePlugin.error(JSON.stringify(Object.values(data)[0]));
  } else {
    await getUserList();
    MessagePlugin.success('删除成功');
  }
};

const handlebatchModelLimit: FormProps['onSubmit'] = async ({ validateResult, firstError }) => {
  if (validateResult === true) {
    batchUpdateUserModelLimit();
  } else {
    console.error('表单引用未定义', firstError);
  }
};

const handleAdd: FormProps['onSubmit'] = async ({ validateResult, firstError }) => {
  console.log('validateResult', validateResult);
  if (validateResult === true) {
    addOrUpdateUser();
  } else {
    console.error('表单引用未定义', firstError);
  }
};

const onModelLimitChange = (value: boolean) => {
  if (value) {
    if (newUser.value.model_limit.length === 0) {
      newUser.value.model_limit = [{}];
    }
    if (batchModelLimitUser.value.model_limit.length === 0) {
      batchModelLimitUser.value.model_limit = [{}];
    }
  } else {
    newUser.value.model_limit = [];
    batchModelLimitUser.value.model_limit = [];
  }
  console.log('onModelLimitChange', value);
};

const getChatGPTDetails = async (user: any) => {
  showChatGPTDetailsDialog.value = true;
  userChatgptDetailsRef.value.getChatGPTDetails(user);
};

onMounted(async () => {
  await getPlanEnum();
  await getUserList();
});
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
