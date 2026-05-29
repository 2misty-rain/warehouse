<template>
  <div class="toolbox-page">
    <el-tabs v-model="tab">
      <el-tab-pane label="账号管理" name="accounts">
        <!-- Toolbar -->
        <div class="ops-toolbar">
          <el-input v-model="searchOrg" placeholder="搜索机构..." size="default" style="width:220px" clearable @change="loadOrgs" />
          <el-button type="primary" size="default" @click="openCreateOrg"><el-icon><Plus /></el-icon> 新增机构</el-button>
          <el-button type="success" size="default" @click="openCreateAcct"><el-icon><User /></el-icon> 为已有机构创建账号</el-button>
        </div>

        <!-- Organization list with accounts -->
        <div v-loading="loading">
          <el-collapse v-model="expanded" @change="onExpand" v-if="orgs.length">
            <el-collapse-item v-for="o in orgs" :key="o.id" :name="o.id">
              <template #title>
                <div class="org-row">
                  <strong>{{ o.short_name }}</strong>
                  <span class="text-muted" style="margin:0 8px;font-size:12px">{{ o.name }}</span>
                  <el-tag size="small" effect="plain">{{ o.title }}</el-tag>
                  <span class="text-muted" style="margin-left:auto;font-size:12px">{{ o.address }}</span>
                </div>
              </template>
              <div v-if="accts[o.id]?.length">
                <el-table :data="accts[o.id]" size="small" stripe>
                  <el-table-column prop="account" label="账号" width="140" />
                  <el-table-column prop="display_name" label="显示名" width="100" />
                  <el-table-column prop="phone_number" label="手机号" width="120" />
                  <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
                  <el-table-column label="Token" width="70" align="center">
                    <template #default="{row}"><el-tag :type="row.has_token?'success':'info'" size="small" round>{{ row.has_token?'有效':'无' }}</el-tag></template>
                  </el-table-column>
                  <el-table-column prop="created_time" label="创建时间" width="130" />
                  <el-table-column label="操作" width="160" align="center">
                    <template #default="{row}">
                      <el-button size="small" text type="warning" @click="resetToken(row)">重置Token</el-button>
                      <el-button size="small" text type="danger" @click="delAcct(row, o.id)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
              <div v-else class="text-muted" style="padding:12px">暂无账号，点击上方按钮创建</div>
            </el-collapse-item>
          </el-collapse>
          <el-empty v-else description="暂无机构" />
        </div>
      </el-tab-pane>
      <el-tab-pane label="更多工具" name="more" disabled><el-empty description="即将上线" /></el-tab-pane>
    </el-tabs>

    <!-- Create Organization Dialog -->
    <el-dialog v-model="orgVisible" title="新增机构" width="520px" destroy-on-close>
      <el-form :model="orgF" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="机构名称" required><el-input v-model="orgF.name" placeholder="全称" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="简称" required><el-input v-model="orgF.short_name" placeholder="简称" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="平台标题"><el-input v-model="orgF.title" placeholder="如：智慧看护平台" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="省编码"><el-input v-model="orgF.province_code" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="市编码"><el-input v-model="orgF.city_code" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="区编码"><el-input v-model="orgF.region_code" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="地址"><el-input v-model="orgF.address" /></el-form-item>
        <el-form-item label="机构性质">
          <el-select v-model="orgF.nature" style="width:100%">
            <el-option :value="1" label="养老机构" /><el-option :value="2" label="康养中心" />
            <el-option :value="3" label="社区服务中心" /><el-option :value="99" label="其他" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="经度"><el-input-number v-model="orgF.lng" :precision="6" :step="0.01" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="纬度"><el-input-number v-model="orgF.lat" :precision="6" :step="0.01" style="width:100%" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="orgVisible=false">取消</el-button><el-button type="primary" @click="doCreateOrg" :loading="creatingOrg">创建机构</el-button></template>
    </el-dialog>

    <!-- Create Account Dialog -->
    <el-dialog v-model="acctVisible" title="创建账号" width="460px" destroy-on-close>
      <el-form :model="acctF" label-width="80px" :rules="acctRules" ref="acctFormRef">
        <el-form-item label="所属机构" prop="org_id">
          <el-select v-model="acctF.org_id" filterable placeholder="选择机构" style="width:100%">
            <el-option v-for="o in orgOptions" :key="o.id" :label="`${o.short_name} - ${o.name}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="登录账号" prop="account"><el-input v-model="acctF.account" placeholder="英文+数字,至少3位" /></el-form-item>
        <el-form-item label="显示名称" prop="display_name"><el-input v-model="acctF.display_name" placeholder="如:张三" /></el-form-item>
        <el-form-item label="密码" prop="password"><el-input v-model="acctF.password" type="password" show-password placeholder="至少6位" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="acctF.phone" placeholder="可选" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="acctF.remark" placeholder="可选" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="acctVisible=false">取消</el-button><el-button type="primary" @click="doCreateAcct" :loading="creatingAcct">创建账号</el-button></template>
    </el-dialog>

    <!-- Token display dialog -->
    <el-dialog v-model="tokenVisible" title="Access Token" width="520px">
      <el-alert type="warning" :closable="false" show-icon title="请复制并妥善保存，关闭后无法再次查看" style="margin-bottom:12px" />
      <el-input v-model="curToken" readonly><template #append><el-button @click="copyToken">复制</el-button></template></el-input>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })
api.interceptors.request.use(c => { c.headers.Authorization = `Bearer ${localStorage.getItem('access_token')}`; return c })
api.interceptors.response.use(r => r.data)

export default {
  name: 'Toolbox',
  setup() {
    const tab=ref('accounts'),loading=ref(false),orgs=ref([]),expanded=ref([]),accts=reactive({}),searchOrg=ref('')

    // Create org
    const orgVisible=ref(false),creatingOrg=ref(false)
    const orgF=reactive({name:'',short_name:'',title:'',province_code:'',city_code:'',region_code:'',address:'',nature:1,lng:null,lat:null})
    const openCreateOrg=()=>{Object.keys(orgF).forEach(k=>orgF[k]=k==='nature'?1:null);orgVisible.value=true}
    const doCreateOrg=async()=>{
      if(!orgF.name||!orgF.short_name){ElMessage.warning('请填写机构名称和简称');return}
      creatingOrg.value=true
      try{
        await api.post('/toolbox/organizations/create',{
          organization_name:orgF.name,organization_short_name:orgF.short_name,title:orgF.title||'',
          organization_nature:orgF.nature||1,province_code:orgF.province_code||'',city_code:orgF.city_code||'',
          region_code:orgF.region_code||'',address:orgF.address||'',center_lng:orgF.lng,center_lat:orgF.lat
        })
        ElMessage.success(`机构"${orgF.short_name}"创建成功`);orgVisible.value=false;await loadOrgs()
      }catch(e){ElMessage.error('创建失败: '+(e.response?.data?.detail||e.message))}
      finally{creatingOrg.value=false}
    }

    // Create account
    const acctVisible=ref(false),creatingAcct=ref(false),acctFormRef=ref(null),orgOptions=ref([])
    const acctF=reactive({org_id:null,account:'',display_name:'',password:'',phone:'',remark:''})
    const acctRules={org_id:[{required:true,message:'请选择机构'}],account:[{required:true,message:'请输入账号',trigger:'blur'},{min:3,message:'至少3位'},{pattern:/^[a-zA-Z0-9_]+$/,message:'仅字母数字下划线'}],display_name:[{required:true,message:'请输入显示名称'}],password:[{required:true,message:'请输入密码'},{min:6,message:'至少6位'}]}
    const openCreateAcct=async()=>{
      acctF.org_id=null;acctF.account='';acctF.display_name='';acctF.password='';acctF.phone='';acctF.remark=''
      try{const r=await api.get('/toolbox/organizations');orgOptions.value=r.organizations||[]}catch{}
      acctVisible.value=true
    }
    const doCreateAcct=async()=>{
      const v=await acctFormRef.value?.validate().catch(()=>false);if(!v)return
      creatingAcct.value=true
      try{
        const r=await api.post('/toolbox/accounts',{organization_id:acctF.org_id,account:acctF.account,display_name:acctF.display_name,password:acctF.password,phone_number:acctF.phone,remark:acctF.remark})
        ElMessage.success(r.message||'创建成功');acctVisible.value=false
        if(r.access_token){curToken.value=r.access_token;tokenVisible.value=true}
        // Refresh
        delete accts[acctF.org_id];await loadAccts(acctF.org_id)
        if(!expanded.value.includes(acctF.org_id))expanded.value.push(acctF.org_id)
      }catch(e){ElMessage.error(e.response?.data?.detail||'创建失败')}
      finally{creatingAcct.value=false}
    }

    // Token
    const tokenVisible=ref(false),curToken=ref('')
    const copyToken=()=>{navigator.clipboard.writeText(curToken.value).then(()=>ElMessage.success('已复制')).catch(()=>ElMessage.info('请手动复制'))}
    const resetToken=async(row)=>{
      try{await ElMessageBox.confirm('确定重置Token?旧Token立即失效','确认',{type:'warning'})}catch{return}
      try{const r=await api.post(`/toolbox/accounts/${row.id}/reset-token`);if(r.access_token){curToken.value=r.access_token;tokenVisible.value=true;ElMessage.success('Token已重置')}}catch(e){ElMessage.error('重置失败')}
    }
    const delAcct=async(row,orgId)=>{
      try{await ElMessageBox.confirm(`确定删除账号"${row.account}"?`,'确认',{type:'warning'})}catch{return}
      try{await api.delete(`/toolbox/accounts/${row.id}`);ElMessage.success('已删除');delete accts[orgId];await loadAccts(orgId)}catch(e){ElMessage.error('删除失败')}
    }

    // Load
    const loadOrgs=async()=>{loading.value=true;try{const p={};if(searchOrg.value)p.search=searchOrg.value;const r=await api.get('/toolbox/organizations',{params:p});orgs.value=r.organizations||[]}catch(e){ElMessage.error('加载机构失败')}finally{loading.value=false}}
    const loadAccts=async(oid)=>{try{const r=await api.get(`/toolbox/organizations/${oid}`);accts[oid]=r.accounts||[]}catch{}}
    const onExpand=val=>{val.forEach(id=>{if(!accts[id])loadAccts(id)})}

    onMounted(()=>loadOrgs())

    return {tab,loading,orgs,expanded,accts,searchOrg,loadOrgs,onExpand,orgVisible,creatingOrg,orgF,openCreateOrg,doCreateOrg,acctVisible,creatingAcct,acctFormRef,orgOptions,acctF,acctRules,openCreateAcct,doCreateAcct,tokenVisible,curToken,copyToken,resetToken,delAcct}
  }
}
</script>

<style scoped>
.toolbox-page { padding: 0; }
.ops-toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
.org-row { display: flex; align-items: center; width: 100%; }
.text-muted { color: #bfbfbf; }
</style>
