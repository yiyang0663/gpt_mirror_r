<template>
  <t-table
    :data="tableChatgptDetailsData"
    :columns="columnsChatgptDetails"
    row-key="chatgpt_username"
    :loading="tableLoading"
    bordered
    hover
  >
    <template #auth_status="{ row }">
      <t-tag v-if="row.auth_status === false" theme="danger" variant="light"> 已过期 </t-tag>
      <t-tag v-if="row.auth_status === true" theme="success" variant="light"> 运行中 </t-tag>
    </template>

    <template #account_type="{ row }">
      <t-tag v-if="row.account_type === 'relay_api'" theme="warning" variant="light"> 中转站 </t-tag>
      <t-tag v-else theme="primary" variant="light"> ChatGPT </t-tag>
    </template>

    <template #proxy_mirror_token="{ row }">
      {{ row.proxy_mirror_token || row.mirror_token }}
    </template>

    <template #op="slotProps">
      <t-link theme="primary" @click="handleCopyToken(slotProps.row.proxy_mirror_token || slotProps.row.mirror_token)">
        复制 Token
      </t-link>
    </template>
  </t-table>
</template>

<script setup lang="ts">
import { MessagePlugin, TableProps } from 'tdesign-vue-next';
import { ref } from 'vue';

import RequestApi from '@/api/request';

interface TableChatgptDetailsData {
  mirror_token: string;
  proxy_mirror_token?: string;
  chatgpt_username: string;
  plan_type: string;
  account_type: string;
}

const tableLoading = ref(false);
const tableChatgptDetailsData = ref<TableChatgptDetailsData[]>([]);

const columnsChatgptDetails: TableProps['columns'] = [
  { colKey: 'chatgpt_username', title: '账号标识', width: 120 },
  { colKey: 'account_type', title: '接入方式', width: 80 },
  { colKey: 'plan_type', title: '类型', width: 50 },
  { colKey: 'auth_status', title: '状态', width: 50 },
  { colKey: 'proxy_mirror_token', title: 'API Token', width: 220 },
  { colKey: 'op', title: '操作', width: 60 },
];

const getChatGPTDetails = async (user: any) => {
  tableLoading.value = true;
  const GptDetailsUri = `/0x/user/get-mirror-token?user_id=${user.id}`;
  const response = await RequestApi(GptDetailsUri);
  const data = await response.json();
  tableChatgptDetailsData.value = data;
  tableLoading.value = false;
  console.log(data);
};

const handleCopyToken = (mirrorToken: string) => {
  navigator.clipboard.writeText(mirrorToken);
  MessagePlugin.success('复制成功');
};

defineExpose({
  getChatGPTDetails,
});
</script>
