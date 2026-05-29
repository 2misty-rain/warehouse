<template>
  <div class="device-monitor">
    <!-- Top Toolbar -->
    <div class="ops-toolbar">
      <div class="ops-toolbar-left">
        <el-button type="primary" @click="refreshAll" :loading="refreshing"><el-icon><Refresh /></el-icon> 刷新</el-button>
        <el-tag v-if="lastCheckTime" size="small" effect="plain">{{ lastCheckTime }}</el-tag>
        <el-button @click="showDbConfig = true"><el-icon><Coin /></el-icon> 生产库</el-button>
      </div>
      <div class="ops-toolbar-right">
        <el-button @click="openFwDialog" v-if="isAdmin"><el-icon><Setting /></el-icon> 固件版本</el-button>
        <el-button type="success" @click="openGroupDialog"><el-icon><Plus /></el-icon> 新建分组</el-button>
      </div>
    </div>

    <!-- KPI Cards -->
    <el-row :gutter="14" class="kpi-row">
      <el-col :span="6"><div class="kpi-card" :class="rateClass"><div class="kpi-value">{{ overallRate }}%</div><div class="kpi-label">整体在线率</div><div class="kpi-sub">{{ onlineCount }}/{{ totalCount }} 在线</div></div></el-col>
      <el-col :span="6"><div class="kpi-card blue"><div class="kpi-value">{{ totalCount }}</div><div class="kpi-label">监控设备</div><div class="kpi-sub">{{ orgCount }} 机构</div></div></el-col>
      <el-col :span="6"><div class="kpi-card" :class="offlineCount>0?'red':'green'"><div class="kpi-value">{{ offlineCount }}</div><div class="kpi-label">离线设备</div><div class="kpi-sub">{{ pendingIncidents }} 待处理</div></div></el-col>
      <el-col :span="6"><div class="kpi-card orange"><div class="kpi-value">{{ needFwCount }}</div><div class="kpi-label">需更新固件</div><div class="kpi-sub">正常版本 {{ currentFw }}</div></div></el-col>
    </el-row>

    <!-- MAIN VIEW -->
    <template v-if="viewMode==='overview'">
      <el-card shadow="never" v-for="group in groups" :key="group.name" class="group-card">
        <template #header>
          <div class="group-header">
            <span class="group-title">{{ group.name }}</span>
            <el-tag size="small" effect="plain">{{ group.orgs.length }}机构·{{ group.totalDevices }}台</el-tag>
            <span style="margin-left:auto;font-size:13px;color:#8c8c8c">在线率 {{ group.onlineRate }}%</span>
          </div>
        </template>
        <el-table :data="group.orgs" stripe highlight-current-row style="cursor:pointer" @row-click="r=>openOrgDetail(r)">
          <el-table-column prop="organization" label="机构" width="150" fixed><template #default="{row}"><strong>{{ row.organization }}</strong></template></el-table-column>
          <el-table-column prop="total_devices" label="总数" width="65" align="center" />
          <el-table-column prop="online_count" label="在线" width="60" align="center"><template #default="{row}"><span class="text-green">{{ row.online_count }}</span></template></el-table-column>
          <el-table-column prop="offline_count" label="离线" width="60" align="center"><template #default="{row}"><span :class="row.offline_count>0?'text-red':''">{{ row.offline_count }}</span></template></el-table-column>
          <el-table-column label="在线率" width="105" align="center">
            <template #default="{row}">
              <div style="display:flex;align-items:center;gap:6px;justify-content:center">
                <el-progress type="circle" :percentage="row.online_rate" :width="30" :stroke-width="6" :color="row.online_rate>=90?'#52c41a':row.online_rate>=70?'#fa8c16':'#f5222d'" :show-text="false" />
                <span style="font-size:13px;font-weight:600">{{ row.online_rate }}%</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="不活跃" width="70" align="center"><template #default><span class="text-muted">-</span></template></el-table-column>
          <el-table-column label="频繁在离线" width="85" align="center"><template #default="{row}"><span v-if="row._freq>0" class="text-red">{{ row._freq }}台</span><span v-else class="text-muted">-</span></template></el-table-column>
          <el-table-column label="需更新" width="70" align="center"><template #default="{row}"><el-tag v-if="row.need_update_count>0" type="warning" size="small" effect="dark" round>{{ row.need_update_count }}</el-tag><span v-else class="text-muted">-</span></template></el-table-column>
          <el-table-column label="趋势" width="70" align="center"><template #default="{row}"><el-button size="small" text type="primary" @click.stop="openTrend(row)">查看</el-button></template></el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- ORG DETAIL VIEW -->
    <template v-else-if="viewMode==='detail'">
      <el-button @click="viewMode='overview'" style="margin-bottom:12px"><el-icon><ArrowLeft /></el-icon> 返回总览</el-button>
      <el-card shadow="never">
        <template #header>
          <div class="detail-bar">
            <strong>{{ detailOrg }}</strong>
            <div style="flex:1"></div>
            <el-radio-group v-model="devFilter" size="small" @change="applyDevFilter">
              <el-radio-button value="">全部</el-radio-button>
              <el-radio-button value="online">在线</el-radio-button>
              <el-radio-button value="offline">离线</el-radio-button>
              <el-radio-button value="freq">频繁在离线</el-radio-button>
              <el-radio-button value="fw">需更新固件</el-radio-button>
            </el-radio-group>
          </div>
        </template>
        <el-table :data="filteredDevices" stripe v-loading="detailLoading">
          <el-table-column prop="device_id" label="设备号" width="155" />
          <el-table-column label="状态" width="90" align="center">
            <template #default="{row}">
              <el-tag :type="row.is_online?'success':'danger'" size="small" effect="dark" round>{{ row.is_online?'在线':'离线' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="频繁在离线" width="95" align="center">
            <template #default="{row}">
              <el-tag v-if="row._is_frequent" type="warning" size="small" effect="dark" round>频繁</el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="离线时长" width="95" align="center">
            <template #default="{row}">{{ row.is_online?'-':fmtDur(row.offline_duration_minutes) }}</template>
          </el-table-column>
          <el-table-column label="固件" width="65" align="center"><template #default="{row}">{{ row.firmware_version||'-' }}</template></el-table-column>
          <el-table-column label="需更新" width="65" align="center"><template #default="{row}"><el-tag v-if="row.needs_firmware_update" type="warning" size="small">是</el-tag><span v-else>-</span></template></el-table-column>
          <el-table-column label="处理状态" width="90" align="center">
            <template #default="{row}">
              <el-tag v-if="row._handle_status==='已解决'" type="success" size="small" effect="dark" round>已解决</el-tag>
              <el-tag v-else-if="row._handle_status==='待解决'" type="warning" size="small" effect="dark" round>待解决</el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="处理备注" min-width="150" show-overflow-tooltip>
            <template #default="{row}">{{ row._handle_note||'-' }}</template>
          </el-table-column>
          <el-table-column label="心跳时间" width="150"><template #default="{row}">{{ row.last_heartbeat||'-' }}</template></el-table-column>
          <el-table-column label="操作" width="100" align="center" fixed="right">
            <template #default="{row}">
              <el-button v-if="!row.is_online && row._handle_status!=='已解决'" type="primary" size="small" @click="openHandle(row)">处理</el-button>
              <el-button v-else-if="!row.is_online && row._handle_status==='已解决'" size="small" @click="openHandle(row)">更新</el-button>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- ORG TREND VIEW -->
    <template v-else-if="viewMode==='trend'">
      <el-button @click="viewMode='overview'" style="margin-bottom:12px"><el-icon><ArrowLeft /></el-icon> 返回总览</el-button>
      <el-card shadow="never">
        <template #header>
          <div class="detail-bar">
            <strong>{{ trendOrg }} · 趋势变化</strong>
            <div style="flex:1"></div>
            <el-radio-group v-model="trendDays" size="small" @change="loadTrend">
              <el-radio-button :value="7">近7天</el-radio-button>
              <el-radio-button :value="30">近30天</el-radio-button>
            </el-radio-group>
            <el-date-picker v-model="trendRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" size="small" style="margin-left:8px;width:240px" @change="loadTrendCustom" />
          </div>
        </template>
        <div v-if="trendData.length" style="padding:8px 0">
          <el-table :data="trendData" stripe size="small">
            <el-table-column prop="date" label="日期" width="110" />
            <el-table-column prop="total" label="设备总数" width="80" align="center" />
            <el-table-column prop="online" label="在线" width="60" align="center"><template #default="{row}"><span class="text-green">{{ row.online }}</span></template></el-table-column>
            <el-table-column prop="offline" label="离线" width="60" align="center"><template #default="{row}"><span :class="row.offline>0?'text-red':''">{{ row.offline }}</span></template></el-table-column>
            <el-table-column label="在线率" width="120" align="center">
              <template #default="{row}">
                <div style="display:flex;align-items:center;gap:6px;justify-content:center">
                  <el-progress type="circle" :percentage="row.online_rate" :width="24" :stroke-width="6" :color="row.online_rate>=90?'#52c41a':row.online_rate>=70?'#fa8c16':'#f5222d'" :show-text="false" />
                  <span style="font-size:12px;font-weight:600">{{ row.online_rate }}%</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="fw_updates" label="需更新固件" width="90" align="center" />
          </el-table>
        </div>
        <el-empty v-else description="暂无趋势数据" />
      </el-card>
    </template>

    <!-- GROUPS -->
    <el-card shadow="never" style="margin-top:14px" v-if="existingGroups.length">
      <template #header><strong>设备分组管理</strong></template>
      <div v-for="g in existingGroups" :key="g.id" class="group-row">
        <div class="group-info">
          <strong>{{ g.name }}</strong><span class="text-muted" style="margin-left:8px;font-size:12px">{{ g.description||'' }}</span>
          <el-tag size="small" style="margin-left:8px">{{ g.device_count }}台</el-tag>
        </div>
        <div class="group-actions">
          <el-button size="small" text type="primary" @click="viewGroupDevs(g)">查看设备</el-button>
          <el-button size="small" text @click="editGroup(g)">修改</el-button>
          <el-button size="small" text type="danger" @click="deleteGroup(g.id)">删除</el-button>
        </div>
        <div v-if="expandedGid===g.id" class="group-detail" v-loading="groupDevsLoading">
          <el-table v-if="groupDevs.length" :data="groupDevs" size="small" stripe>
            <el-table-column prop="device_id" label="设备号" width="150" />
            <el-table-column label="在线" width="60" align="center"><template #default="{row}"><el-tag :type="row.is_online?'success':'danger'" size="small" effect="dark" round>{{ row.is_online?'是':'否' }}</el-tag></template></el-table-column>
            <el-table-column prop="firmware_version" label="固件" width="60" align="center" />
            <el-table-column label="操作" width="80" align="center"><template #default="{row}"><el-button size="small" text type="danger" @click="removeFromGroup(g.id,row.device_id)">移除</el-button></template></el-table-column>
          </el-table>
          <div v-else class="text-muted" style="padding:12px">该分组暂无设备状态数据</div>
        </div>
      </div>
    </el-card>

    <!-- === DIALOGS === -->

    <!-- Handle incident - diversified -->
    <el-dialog v-model="handleVisible" title="处理离线设备" width="480px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="设备号"><strong>{{ handleTarget?.device_id }}</strong></el-form-item>
        <el-form-item label="处理状态" required>
          <el-radio-group v-model="handleForm.status">
            <el-radio value="resolved">已解决</el-radio>
            <el-radio value="pending">待解决</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="原因">
          <el-select v-model="handleForm.reason" style="width:100%" placeholder="选择原因（可选）">
            <el-option label="用户断电" value="用户断电" />
            <el-option label="网络故障" value="网络故障" />
            <el-option label="设备故障" value="设备故障" />
            <el-option label="用户自行处理" value="用户自行处理" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="排期" v-if="handleForm.status==='pending'">
          <el-date-picker v-model="handleForm.schedule" type="date" placeholder="计划处理日期（可选）" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="handleForm.notes" type="textarea" :rows="3" placeholder="处理详情..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleVisible=false">取消</el-button>
        <el-button type="primary" @click="submitHandle" :loading="handling">确认</el-button>
      </template>
    </el-dialog>

    <!-- Firmware -->
    <el-dialog v-model="showFwDialog" title="固件版本" width="400px" destroy-on-close>
      <el-form label-width="110px">
        <el-form-item label="正常版本"><el-input v-model="fwVersion" placeholder="2.55" /></el-form-item>
        <el-form-item label="当前配置"><el-tag v-if="currentFw" type="success">{{ currentFw }}</el-tag><span v-else class="text-muted">未配置</span></el-form-item>
        <el-alert type="info" :closable="false" show-icon>低于此版本标记为需更新</el-alert>
      </el-form>
      <template #footer><el-button @click="showFwDialog=false">取消</el-button><el-button type="primary" @click="saveFw" :loading="savingFw">保存</el-button></template>
    </el-dialog>

    <!-- New group -->
    <el-dialog v-model="showGroupDialog" title="新建分组" width="520px" destroy-on-close @opened="loadDevOpts">
      <el-form label-width="80px">
        <el-form-item label="名称" required><el-input v-model="gf.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="gf.desc" /></el-form-item>
        <el-form-item label="设备"><el-select v-model="gf.ids" multiple filterable placeholder="搜索设备号" style="width:100%" :loading="loadingDevOpts"><el-option v-for="d in allDevOpts" :key="d.value" :label="d.label" :value="d.value" /></el-select><div style="font-size:11px;color:#909399;margin-top:4px">已选 {{ gf.ids.length }} 台</div></el-form-item>
      </el-form>
      <template #footer><el-button @click="showGroupDialog=false">取消</el-button><el-button type="primary" @click="doCreateGroup" :loading="creatingGroup">创建</el-button></template>
    </el-dialog>

    <!-- Edit group -->
    <el-dialog v-model="showEditG" title="修改分组" width="520px" destroy-on-close @opened="loadDevOpts">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="egf.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="egf.desc" /></el-form-item>
        <el-form-item label="设备"><el-select v-model="egf.ids" multiple filterable placeholder="搜索设备号" style="width:100%"><el-option v-for="d in allDevOpts" :key="d.value" :label="d.label" :value="d.value" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="showEditG=false">取消</el-button><el-button type="primary" @click="doUpdateGroup" :loading="updatingGroup">保存</el-button></template>
    </el-dialog>

    <!-- DB config (abbreviated) -->
    <el-dialog v-model="showDbConfig" title="生产数据库" width="560px" destroy-on-close>
      <el-form :model="dbForm" label-width="100px" size="small">
        <el-row :gutter="12"><el-col :span="16"><el-form-item label="主机"><el-input v-model="dbForm.host" /></el-form-item></el-col><el-col :span="8"><el-form-item label="端口"><el-input-number v-model="dbForm.port" :min="1" :max="65535" /></el-form-item></el-col></el-row>
        <el-row :gutter="12"><el-col :span="12"><el-form-item label="数据库"><el-input v-model="dbForm.database" /></el-form-item></el-col><el-col :span="12"><el-form-item label="用户"><el-input v-model="dbForm.username" /></el-form-item></el-col></el-row>
        <el-form-item label="密码"><el-input v-model="dbForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="设备表"><el-input v-model="dbForm.device_table" /></el-form-item>
        <el-form-item label="设备号字段"><el-input v-model="dbForm.device_id_column" /></el-form-item>
        <el-form-item label="在线字段"><el-input v-model="dbForm.online_status_column" /></el-form-item>
        <el-form-item label="心跳字段"><el-input v-model="dbForm.last_heartbeat_column" /></el-form-item>
        <el-form-item label="固件字段"><el-input v-model="dbForm.firmware_version_column" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="testDbConn" :loading="testingDb">测试</el-button><el-button type="primary" @click="saveDbCfg" :loading="savingDb">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { opsAPI, inventoryAPI } from '../api/index.js'
import axios from 'axios'

const ax = axios.create({baseURL:'/api'})
ax.interceptors.request.use(c=>{c.headers.Authorization=`Bearer ${localStorage.getItem('access_token')}`;return c})
ax.interceptors.response.use(r=>r.data)

export default {
  name: 'DeviceMonitor',
  setup() {
    const u=JSON.parse(localStorage.getItem('user_info')||'{}')
    const isAdmin=computed(()=>u.role==='admin')
    const loading=ref(false),refreshing=ref(false),orgData=ref([]),lastCheckTime=ref(null)
    const overallRate=ref(0),onlineCount=ref(0),totalCount=ref(0),offlineCount=ref(0),orgCount=ref(0),needFwCount=ref(0),currentFw=ref(''),pendingIncidents=ref(0)
    const rateClass=computed(()=>overallRate.value>=90?'green':overallRate.value>=70?'orange':'red')

    const groups=computed(()=>{
      const d={name:'商机交付',orgs:[],totalDevices:0,onlineRate:0}
      const t={name:'商机试用',orgs:[],totalDevices:0,onlineRate:0}
      for(const o of orgData.value){const g=o._attr==='商机交付'?d:t;g.orgs.push(o);g.totalDevices+=o.total_devices}
      if(d.totalDevices)d.onlineRate=Math.round(d.orgs.reduce((s,o)=>s+o.online_count,0)/d.totalDevices*100)
      if(t.totalDevices)t.onlineRate=Math.round(t.orgs.reduce((s,o)=>s+o.online_count,0)/t.totalDevices*100)
      return[d,t].filter(g=>g.totalDevices>0)
    })

    // Views
    const viewMode=ref('overview')
    const detailOrg=ref(''),detailDevices=ref([]),detailLoading=ref(false),devFilter=ref('')
    const filteredDevices=computed(()=>{
      if(!devFilter.value)return detailDevices.value
      if(devFilter.value==='online')return detailDevices.value.filter(d=>d.is_online)
      if(devFilter.value==='offline')return detailDevices.value.filter(d=>!d.is_online)
      if(devFilter.value==='freq')return detailDevices.value.filter(d=>d._is_frequent)
      if(devFilter.value==='fw')return detailDevices.value.filter(d=>d.needs_firmware_update)
      return detailDevices.value
    })

    // Trend
    const trendOrg=ref(''),trendData=ref([]),trendDays=ref(7),trendRange=ref(null)

    // Groups
    const existingGroups=ref([]),expandedGid=ref(null),groupDevs=ref([]),groupDevsLoading=ref(false)
    const showGroupDialog=ref(false),creatingGroup=ref(false),loadingDevOpts=ref(false),allDevOpts=ref([])
    const gf=reactive({name:'',desc:'',ids:[]})
    const showEditG=ref(false),updatingGroup=ref(false),editingGid=ref(null)
    const egf=reactive({name:'',desc:'',ids:[]})

    // Handle
    const handleVisible=ref(false),handleTarget=ref(null),handling=ref(false)
    const handleForm=reactive({status:'resolved',reason:'',schedule:'',notes:''})

    // FW
    const showFwDialog=ref(false),fwVersion=ref(''),savingFw=ref(false)

    // DB
    const showDbConfig=ref(false),testingDb=ref(false),savingDb=ref(false)
    const dbForm=reactive({host:'',port:3306,database:'',username:'',password:'',device_table:'operation_device',device_id_column:'device_id',online_status_column:'status',last_heartbeat_column:'last_online_time',firmware_version_column:'version'})

    const fmtDur=m=>m?(m>=60?Math.floor(m/60)+'h'+m%60+'m':m+'m'):'0m'

    // ===== LOAD =====
    const loadAll=async()=>{
      loading.value=true
      try{
        const[ov,inc,grp,fw,db]=await Promise.all([
          opsAPI.getDeviceOverview(),opsAPI.getOfflineIncidents({status:'待处理'}),
          opsAPI.getGroups().catch(()=>({groups:[]})),
          opsAPI.getFirmwareConfig().catch(()=>({config:null})),
          opsAPI.getDbConfig().catch(()=>({config:null})),
        ])
        if(ov.success){
          orgData.value=(ov.organizations||[]).map(o=>({...o,_attr:o._attr||'商机交付'}))
          overallRate.value=ov.total_online_rate||0;lastCheckTime.value=ov.check_time
          let t=0,on=0,off=0,fw=0
          for(const o of ov.organizations||[]){t+=o.total_devices;on+=o.online_count;off+=o.offline_count;fw+=o.need_update_count||0}
          totalCount.value=t;onlineCount.value=on;offlineCount.value=off;orgCount.value=(ov.organizations||[]).length;needFwCount.value=fw
          // Mark frequent on/off for orgs (placeholder: >2 offline devices = frequent)
          for(const o of orgData.value) o._freq=Math.max(0,o.offline_count-1)
        }
        pendingIncidents.value=(inc.items||[]).filter(i=>i.status==='待处理').length
        existingGroups.value=grp.groups||[]
        if(fw.config){currentFw.value=fw.config.current_normal_version;fwVersion.value=fw.config.current_normal_version}
        if(db.config){Object.assign(dbForm,db.config);if(dbForm.password==='******')dbForm.password=''}
      }catch(e){ElMessage.error('加载失败')}
      finally{loading.value=false}
    }
    const refreshAll=async()=>{
      refreshing.value=true
      try{const r=await opsAPI.refreshDeviceStatus();if(r.success){ElMessage.success(`同步${r.synced}台`);await loadAll()}else ElMessage.warning(r.detail||'请先配置生产库')}
      catch(e){ElMessage.error('刷新失败')}
      finally{refreshing.value=false}
    }

    // ===== DETAIL =====
    const openOrgDetail=async(row)=>{
      detailOrg.value=row.organization;viewMode.value='detail'
      await loadOrgDevices()
    }
    const loadOrgDevices=async()=>{
      detailLoading.value=true
      try{
        const[dr,ir]=await Promise.all([
          opsAPI.getDeviceDetail({organization:detailOrg.value}),
          opsAPI.getOfflineIncidents({organization:detailOrg.value,limit:200}),
        ])
        // Build incident map: device_id -> latest handling info
        const incMap={}
        for(const i of ir.items||[]){
          if(!incMap[i.device_id]||new Date(i.updated_at||i.created_at)>new Date(incMap[i.device_id].updated_at||incMap[i.device_id].created_at)){
            incMap[i.device_id]=i
          }
        }
        detailDevices.value=(dr.devices||[]).map(d=>{
          const inc=incMap[d.device_id]
          const note=inc?.notes||''
          const isResolved=note.includes('[已解决]')
          const isPending=note.includes('[待解决]')||note.includes('[排期:')
          return{
            ...d,
            _is_frequent:!d.is_online&&(d.offline_duration_minutes||0)>0&&(d.offline_duration_minutes||0)<120,
            _handle_status:isResolved?'已解决':isPending?'待解决':(inc&&inc.status==='已处理'?'已解决':''),
            _handle_note:note||(inc?`${inc.reason_tag||''} ${inc.status||''}`:''),
          }
        })
      }catch(e){ElMessage.error('加载失败:'+(e.response?.data?.detail||e.message))}
      finally{detailLoading.value=false}
    }
    const applyDevFilter=()=>{} // computed handles it

    // ===== HANDLE =====
    const openHandle=(dev)=>{
      handleTarget.value=dev
      // Pre-fill from existing handling info
      const note=dev._handle_note||''
      if(note.includes('[已解决]'))handleForm.status='resolved'
      else if(note.includes('[待解决]')||note.includes('[排期:'))handleForm.status='pending'
      else handleForm.status='resolved'
      // Extract reason
      const rm=note.match(/原因:(\S+)/)
      handleForm.reason=rm?rm[1]:''
      // Extract schedule
      const sm=note.match(/排期:(\d{4}-\d{2}-\d{2})/)
      handleForm.schedule=sm?sm[1]:''
      handleForm.notes=note||''
      handleVisible.value=true
    }
    const submitHandle=async()=>{
      handling.value=true
      try{
        // Find or create incident
        const r=await opsAPI.getOfflineIncidents({status:'待处理'})
        const inc=(r.items||[]).find(i=>i.device_id===handleTarget.value.device_id)
        const note=(handleForm.status==='pending'?(handleForm.schedule?`[排期:${handleForm.schedule}] `:'[待解决] '):'[已解决] ')+
          (handleForm.reason?`原因:${handleForm.reason} `:'')+(handleForm.notes||'')
        if(inc){
          await opsAPI.handleIncident(inc.id,{reason_tag:handleForm.reason||'其他',notes:note})
        }
        if(handleForm.reason==='用户断电'){
          // Also silence future incidents
          try{await ax.post('/operations/anomaly-ignore-rules',{device_id:handleTarget.value.device_id,reason:'设备监控-用户断电'})}catch{}
        }
        ElMessage.success(handleForm.status==='resolved'?'已标记为已解决':'已标记为待解决')
        handleVisible.value=false;await loadOrgDevices()
      }catch(e){ElMessage.error('处理失败:'+(e.response?.data?.detail||e.message))}
      finally{handling.value=false}
    }

    // ===== TREND =====
    const openTrend=async(row)=>{
      trendOrg.value=row.organization;trendDays.value=7;trendRange.value=null;viewMode.value='trend'
      await loadTrend()
    }
    const loadTrend=async()=>{
      try{
        const r=await ax.get('/operations/device-status/org-trend',{params:{org:trendOrg.value,days:trendDays.value}})
        trendData.value=r.trend||[]
      }catch{trendData.value=[]}
    }
    const loadTrendCustom=async()=>{
      if(!trendRange.value||trendRange.value.length!==2)return
      const d1=new Date(trendRange.value[0]),d2=new Date(trendRange.value[1])
      const days=Math.ceil((d2-d1)/86400000)+1
      trendDays.value=Math.min(days,90)
      await loadTrend()
    }

    // ===== GROUPS =====
    const loadDevOpts=async()=>{
      loadingDevOpts.value=true
      try{const r=await inventoryAPI.getAll({limit:10000});allDevOpts.value=(r.items||[]).map(d=>({value:d.device_id,label:`${d.device_id} (${d.owner||'-'} | ${d.device_attribute||'-'})`}))}
      catch{allDevOpts.value=[]}
      finally{loadingDevOpts.value=false}
    }
    const openGroupDialog=()=>{gf.name='';gf.desc='';gf.ids=[];showGroupDialog.value=true}
    const doCreateGroup=async()=>{
      if(!gf.name.trim()){ElMessage.warning('请输入名称');return}
      creatingGroup.value=true
      try{await opsAPI.createGroup({name:gf.name.trim(),description:gf.desc,device_ids:gf.ids});ElMessage.success('创建成功');showGroupDialog.value=false;await loadAll()}
      catch(e){ElMessage.error('创建失败')}
      finally{creatingGroup.value=false}
    }
    const viewGroupDevs=async(g)=>{
      if(expandedGid.value===g.id){expandedGid.value=null;return}
      expandedGid.value=g.id
      if(!(g.device_ids||[]).length){groupDevs.value=[];return}
      groupDevsLoading.value=true
      try{
        // Query all devices, then filter by group's device_ids
        const ids=new Set(g.device_ids||[])
        const r=await opsAPI.getDeviceDetail({limit:500})
        groupDevs.value=(r.devices||[]).filter(d=>ids.has(d.device_id))
        if(!groupDevs.value.length)ElMessage.info('该分组设备暂无状态数据')
      }catch(e){groupDevs.value=[];ElMessage.error('加载失败')}
      finally{groupDevsLoading.value=false}
    }
    const editGroup=(g)=>{editingGid.value=g.id;egf.name=g.name;egf.desc=g.description||'';egf.ids=[...(g.device_ids||[])];showEditG.value=true}
    const doUpdateGroup=async()=>{
      updatingGroup.value=true
      try{await opsAPI.updateGroup(editingGid.value,{name:egf.name,description:egf.desc,device_ids:egf.ids});ElMessage.success('已更新');showEditG.value=false;await loadAll();expandedGid.value=null}
      catch(e){ElMessage.error('更新失败')}
      finally{updatingGroup.value=false}
    }
    const deleteGroup=async(gid)=>{
      try{await ElMessageBox.confirm('确定删除?','确认',{type:'warning'})}catch{return}
      try{await opsAPI.deleteGroup(gid);ElMessage.success('已删除');await loadAll()}catch(e){ElMessage.error('删除失败')}
    }
    const removeFromGroup=async(gid,did)=>{
      const g=existingGroups.value.find(x=>x.id===gid)
      if(!g){ElMessage.error('分组不存在');return}
      const ids=(g.device_ids||[]).filter(x=>x!==did)
      try{
        await opsAPI.updateGroup(gid,{device_ids:ids})
        ElMessage.success('已移除')
        // Update local cache
        g.device_ids=ids
        g.device_count=ids.length
        // Refresh expanded view
        groupDevs.value=groupDevs.value.filter(d=>d.device_id!==did)
      }catch(e){ElMessage.error('移除失败: '+(e.response?.data?.detail||e.message))}
    }

    // ===== FW =====
    const openFwDialog=async()=>{
      showFwDialog.value=true
      try{const r=await opsAPI.getFirmwareConfig();if(r.config){currentFw.value=r.config.current_normal_version;fwVersion.value=r.config.current_normal_version}}catch{}
    }
    const saveFw=async()=>{
      if(!fwVersion.value.trim()){ElMessage.warning('请输入版本号');return}
      savingFw.value=true
      try{await opsAPI.setFirmwareConfig({current_normal_version:fwVersion.value.trim()});ElMessage.success('已保存');currentFw.value=fwVersion.value.trim();showFwDialog.value=false}
      catch(e){ElMessage.error('保存失败')}
      finally{savingFw.value=false}
    }

    // ===== DB =====
    const testDbConn=async()=>{
      testingDb.value=true
      try{const r=await opsAPI.testDbConnection({host:dbForm.host,port:dbForm.port,database:dbForm.database,username:dbForm.username,password:dbForm.password});if(r.success)ElMessage.success('连接成功');else ElMessage.error(r.detail)}
      catch{ElMessage.error('测试失败')}
      finally{testingDb.value=false}
    }
    const saveDbCfg=async()=>{
      savingDb.value=true
      try{await opsAPI.saveDbConfig({...dbForm});ElMessage.success('已保存');showDbConfig.value=false}
      catch{ElMessage.error('保存失败')}
      finally{savingDb.value=false}
    }

    onMounted(()=>loadAll())

    return{loading,refreshing,orgData,lastCheckTime,overallRate,onlineCount,totalCount,offlineCount,orgCount,needFwCount,currentFw,pendingIncidents,rateClass,groups,refreshAll,
      viewMode,detailOrg,detailDevices,detailLoading,devFilter,filteredDevices,openOrgDetail,loadOrgDevices,applyDevFilter,
      trendOrg,trendData,trendDays,trendRange,openTrend,loadTrend,loadTrendCustom,
      existingGroups,expandedGid,groupDevs,groupDevsLoading,showGroupDialog,creatingGroup,loadingDevOpts,allDevOpts,gf,openGroupDialog,doCreateGroup,
      showEditG,updatingGroup,egf,editGroup,doUpdateGroup,viewGroupDevs,deleteGroup,removeFromGroup,
      handleVisible,handleTarget,handling,handleForm,openHandle,submitHandle,fmtDur,
      showFwDialog,fwVersion,savingFw,openFwDialog,saveFw,
      showDbConfig,testingDb,savingDb,dbForm,testDbConn,saveDbCfg,
      isAdmin}
  }
}
</script>

<style scoped>
.device-monitor{padding:0}
.ops-toolbar{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap}
.ops-toolbar-left,.ops-toolbar-right{display:flex;align-items:center;gap:8px}
.kpi-row{margin-bottom:14px}
.kpi-card{background:#fff;border-radius:12px;padding:18px;position:relative;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.04);transition:transform .2s,box-shadow .2s}
.kpi-card:hover{transform:translateY(-2px);box-shadow:0 4px 20px rgba(0,0,0,.1)}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px}
.kpi-card.green::before{background:linear-gradient(90deg,#52c41a,#73d13d)}
.kpi-card.blue::before{background:linear-gradient(90deg,#1a73e8,#4dabf7)}
.kpi-card.orange::before{background:linear-gradient(90deg,#fa8c16,#ffc069)}
.kpi-card.red::before{background:linear-gradient(90deg,#f5222d,#ff7875)}
.kpi-value{font-size:30px;font-weight:700}
.kpi-label{font-size:12px;color:#8c8c8c;margin-top:4px}
.kpi-sub{font-size:11px;color:#bfbfbf;margin-top:2px}
.group-card{margin-bottom:14px}
.group-header{display:flex;align-items:center;gap:10px}
.group-title{font-weight:700;font-size:15px}
.detail-bar{display:flex;align-items:center;gap:10px}
.group-row{padding:10px 0;border-bottom:1px solid #f5f5f5}
.group-row:last-child{border-bottom:none}
.group-info{display:flex;align-items:center;margin-bottom:6px}
.group-actions{display:flex;gap:4px}
.group-detail{margin-top:8px;padding:8px;background:#fafafa;border-radius:8px}
.text-green{color:#52c41a;font-weight:600}
.text-red{color:#f5222d;font-weight:600}
.text-muted{color:#bfbfbf}
</style>
