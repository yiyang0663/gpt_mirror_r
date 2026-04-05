<template>
  <div>
    <t-card class="list-card-container">
      <t-row justify="space-between">
        <div class="left-operation-container">
          <t-button @click="handleShowDialog">新增套餐</t-button>
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
      >
        <template #is_active="{ row }">
          <t-tag v-if="row.is_active" theme="success" variant="light">启用</t-tag>
          <t-tag v-else theme="warning" variant="light">停用</t-tag>
        </template>

        <template #allow_web="{ row }">
          {{ row.allow_web ? '是' : '否' }}
        </template>

        <template #allow_api="{ row }">
          {{ row.allow_api ? '是' : '否' }}
        </template>

        <template #quota_rules="{ row }">
          <div v-if="row.quota_rules?.length" class="rule-list">
            <t-tag v-for="item in row.quota_rules" :key="item.id || `${item.period}-${item.channel}-${item.model_name}`" variant="light">
              {{ formatRule(item) }}
            </t-tag>
          </div>
          <span v-else>-</span>
        </template>

        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleEdit(row)">编辑</t-link>
            <t-link theme="danger" @click="handleClickDelete(row)">删除</t-link>
          </t-space>
        </template>
      </t-table>

      <t-dialog v-model:visible="showDialog" :on-confirm="handleConfirm" :header="actionType === 'edit' ? '编辑套餐' : '新增套餐'" width="960px">
        <t-form ref="planFormRef" :data="planForm" :label-width="110" @submit="handleSubmit">
          <t-form-item label="启用状态">
            <t-switch v-model="planForm.is_active" :custom-value="[true, false]" />
          </t-form-item>

          <t-form-item label="套餐名称">
            <t-input v-model="planForm.name" style="width: 260px" />
          </t-form-item>

          <t-form-item label="套餐编码">
            <t-input v-model="planForm.code" style="width: 260px" />
          </t-form-item>

          <t-form-item label="月费">
            <t-input-number v-model="planForm.monthly_price" theme="normal" :min="0" />
          </t-form-item>

          <t-form-item label="展示顺序">
            <t-input-number v-model="planForm.display_order" theme="normal" :min="0" />
          </t-form-item>

          <t-form-item label="网页可用">
            <t-switch v-model="planForm.allow_web" :custom-value="[true, false]" />
          </t-form-item>

          <t-form-item label="API 可用">
            <t-switch v-model="planForm.allow_api" :custom-value="[true, false]" />
          </t-form-item>

          <t-form-item label="配额规则">
            <t-space direction="vertical" style="width: 100%">
              <div v-for="(rule, idx) in planForm.quota_rules" :key="`${rule.id || 'new'}-${idx}`" class="rule-editor">
                <t-space align="center" wrap>
                  <t-select v-model="rule.channel" style="width: 100px">
                    <t-option v-for="item in channelOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </t-select>
                  <t-select v-model="rule.period" style="width: 100px">
                    <t-option v-for="item in periodOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </t-select>
                  <t-input v-model="rule.model_name" placeholder="留空表示全部模型" style="width: 180px" />
                  <t-input-number v-model="rule.request_limit" theme="normal" :min="0" style="width: 120px" />
                  <t-input-number v-model="rule.token_limit" theme="normal" :min="0" style="width: 140px" />
                  <t-switch v-model="rule.enabled" :custom-value="[true, false]" />
                  <t-button theme="danger" variant="outline" @click="removeRule(idx)">删除</t-button>
                </t-space>
              </div>
              <t-button variant="outline" @click="addRule">新增规则</t-button>
            </t-space>
          </t-form-item>

          <t-form-item label="备注">
            <t-textarea v-model="planForm.remark" />
          </t-form-item>
        </t-form>
      </t-dialog>

      <t-dialog v-model:visible="dialogVisibleDelete" header="确认删除该套餐吗" width="520" :on-confirm="handleDelete" />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { MessagePlugin, TableProps } from 'tdesign-vue-next';
import { onMounted, ref } from 'vue';

import RequestApi from '@/api/request';

interface QuotaRuleLine {
  id?: number;
  model_name: string;
  channel: string;
  period: string;
  request_limit: number;
  token_limit: number;
  enabled: boolean;
  remark?: string;
}

interface PlanForm {
  id?: number;
  name: string;
  code: string;
  is_active: boolean;
  allow_web: boolean;
  allow_api: boolean;
  monthly_price: number;
  display_order: number;
  remark: string;
  quota_rules: QuotaRuleLine[];
}

const PlanUri = '/0x/plan/';
const tableLoading = ref(false);
const tableData = ref<any[]>([]);
const showDialog = ref(false);
const dialogVisibleDelete = ref(false);
const planFormRef = ref();
const actionType = ref('add');
const deletePlanId = ref<number | null>(null);

const channelOptions = [
  { label: '全部', value: 'all' },
  { label: '网页', value: 'web' },
  { label: 'API', value: 'api' },
];

const periodOptions = [
  { label: '每日', value: 'daily' },
  { label: '每月', value: 'monthly' },
];

const defaultPlanForm = (): PlanForm => ({
  name: '',
  code: '',
  is_active: true,
  allow_web: true,
  allow_api: true,
  monthly_price: 0,
  display_order: 100,
  remark: '',
  quota_rules: [],
});

const planForm = ref<PlanForm>(defaultPlanForm());

const pagination = {
  defaultPageSize: 20,
  total: 0,
  defaultCurrent: 1,
};

const columns: TableProps['columns'] = [
  { colKey: 'name', title: '套餐', width: 150 },
  { colKey: 'code', title: '编码', width: 130 },
  { colKey: 'is_active', title: '状态', width: 90 },
  { colKey: 'allow_web', title: '网页', width: 70 },
  { colKey: 'allow_api', title: 'API', width: 70 },
  { colKey: 'monthly_price', title: '月费', width: 90 },
  { colKey: 'subscription_count', title: '用户数', width: 80 },
  { colKey: 'quota_rules', title: '规则', width: 520 },
  { colKey: 'remark', title: '备注', width: 180 },
  { colKey: 'op', title: '操作', width: 120, fixed: 'right' },
];

const formatRule = (rule: QuotaRuleLine) => {
  const modelLabel = rule.model_name || '全部模型';
  const channelLabel = channelOptions.find((item) => item.value === rule.channel)?.label || rule.channel;
  const periodLabel = periodOptions.find((item) => item.value === rule.period)?.label || rule.period;
  const requestLabel = rule.request_limit ? `${rule.request_limit} 次` : '请求不限';
  const tokenLabel = rule.token_limit ? `${rule.token_limit} tokens` : 'tokens 不限';
  return `${channelLabel} / ${periodLabel} / ${modelLabel} / ${requestLabel} / ${tokenLabel}`;
};

const rehandlePageChange = (curr: any) => {
  pagination.defaultCurrent = curr.current;
  pagination.defaultPageSize = curr.pageSize;
  getPlanList();
};

const getPlanList = async () => {
  tableLoading.value = true;
  const params: any = {
    page: pagination.defaultCurrent,
    page_size: pagination.defaultPageSize,
  };
  const queryString = new URLSearchParams(params).toString();
  const response = await RequestApi(`${PlanUri}?${queryString}`);
  const data = await response.json();
  tableData.value = data.results;
  pagination.total = data.count;
  tableLoading.value = false;
};

const addRule = () => {
  planForm.value.quota_rules.push({
    model_name: '',
    channel: 'api',
    period: 'monthly',
    request_limit: 0,
    token_limit: 0,
    enabled: true,
  });
};

const removeRule = (idx: number) => {
  planForm.value.quota_rules.splice(idx, 1);
};

const handleShowDialog = () => {
  actionType.value = 'add';
  planForm.value = defaultPlanForm();
  showDialog.value = true;
};

const handleEdit = (row: any) => {
  actionType.value = 'edit';
  planForm.value = {
    id: row.id,
    name: row.name,
    code: row.code,
    is_active: row.is_active,
    allow_web: row.allow_web,
    allow_api: row.allow_api,
    monthly_price: Number(row.monthly_price || 0),
    display_order: row.display_order,
    remark: row.remark || '',
    quota_rules: (row.quota_rules || []).map((item: any) => ({
      id: item.id,
      model_name: item.model_name || '',
      channel: item.channel,
      period: item.period,
      request_limit: item.request_limit || 0,
      token_limit: item.token_limit || 0,
      enabled: item.enabled,
      remark: item.remark || '',
    })),
  };
  showDialog.value = true;
};

const handleClickDelete = (row: any) => {
  deletePlanId.value = row.id;
  dialogVisibleDelete.value = true;
};

const handleDelete = async () => {
  const response = await RequestApi(PlanUri, 'DELETE', { id: deletePlanId.value });
  const data = await response.json();
  dialogVisibleDelete.value = false;
  deletePlanId.value = null;

  if (response.status !== 200) {
    MessagePlugin.error(JSON.stringify(Object.values(data)[0] || data.message || data));
    return;
  }

  await getPlanList();
  MessagePlugin.success('删除成功');
};

const handleConfirm = () => {
  if (planFormRef.value) {
    planFormRef.value.submit();
  }
};

const handleSubmit = async () => {
  const payload = {
    ...planForm.value,
    code: planForm.value.code.trim(),
    name: planForm.value.name.trim(),
    quota_rules: planForm.value.quota_rules.map((item) => ({
      ...item,
      model_name: item.model_name.trim(),
    })),
  };

  const response = await RequestApi(PlanUri, actionType.value === 'edit' ? 'PUT' : 'POST', payload);
  const data = await response.json();
  if (response.status !== 200) {
    MessagePlugin.error(JSON.stringify(Object.values(data)[0] || data.message || data));
    return;
  }

  showDialog.value = false;
  await getPlanList();
  MessagePlugin.success(actionType.value === 'edit' ? '更新成功' : '创建成功');
};

onMounted(async () => {
  await getPlanList();
});
</script>

<style scoped lang="less">
.left-operation-container {
  padding: 6px 0;
  margin-bottom: 16px;
}

.rule-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rule-editor {
  width: 100%;
}
</style>
