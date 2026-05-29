<template>
  <div class="anomaly-page">
    <!-- Toolbar -->
    <div class="ops-toolbar">
      <div class="ops-toolbar-left">
        <el-date-picker v-model="filterDate" type="date" placeholder="筛选日期" value-format="YYYY-MM-DD" size="default" @change="onDateFilter" clearable />
        <el-select v-model="filterInst" placeholder="机构" size="default" clearable style="width:150px" @change="loadRecords">
          <el-option v-for="i in allInstitutions" :key="i" :label="i" :value="i" />
        </el-select>
        <el-select v-model="filterType" placeholder="异常类型" size="default" clearable style="width:140px" @change="loadRecords">
          <el-option label="睡眠状态异常" value="睡眠状态异常" />
          <el-option label="睡眠过少" value="睡眠过少" />
          <el-option label="多次离床" value="多次离床" />
          <el-option label="体征异常" value="体征异常" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索老人/设备/机构..." size="default" style="width:200px" clearable @change="loadRecords" />
      </div>
      <div class="ops-toolbar-right">
        <el-button size="default" @click="syncNow" :loading="syncing"><el-icon><Refresh /></el-icon> 同步数据</el-button>
        <el-button size="default" @click="exportExcel"><el-icon><Download /></el-icon> 导出Excel</el-button>
        <el-button size="default" @click="showIgnoreList = true"><el-icon><Hide /></el-icon> 不考虑列表</el-button>
      </div>
    </div>

    <!-- Status cards -->
    <el-row :gutter="12" class="kpi-row">
      <el-col :span="4" v-for="s in statusList" :key="s.key">
        <div class="kpi-card small" :class="{active: activeStatus === s.key}" @click="switchStatus(s.key)" :style="{cursor:'pointer'}">
          <div class="kpi-value" :style="{color:s.color, fontSize:'26px'}">{{ stats[s.key] || 0 }}</div>
          <div class="kpi-label">{{ s.label }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- Records table -->
    <el-card shadow="never">
      <el-table :data="records" stripe v-loading="loading" @row-click="openDetail" highlight-current-row style="cursor:pointer">
        <el-table-column prop="record_date" label="日期" width="95" />
        <el-table-column label="优先级" width="70" align="center">
          <template #default="{row}">
            <el-tag :type="row.priority==='高'?'danger':row.priority==='中'?'warning':'info'" size="small" effect="dark" round>{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="institution" label="机构" width="110" />
        <el-table-column prop="person_name" label="老人" width="80" />
        <el-table-column prop="device_id" label="设备号" width="145" />
        <el-table-column prop="anomaly_type" label="异常类型" width="115">
          <template #default="{row}">
            <el-tag :type="row.anomaly_type==='体征异常'?'info':'danger'" size="small" round>{{ row.anomaly_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="anomaly_detail" label="异常详情" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="85" align="center">
          <template #default="{row}">
            <el-tag :type="statusColor(row.status)" size="small" effect="dark" round>{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="algorithm_tag" label="算法标记" width="95" align="center">
          <template #default="{row}">
            <el-tag v-if="row.algorithm_tag" :type="tagColor(row.algorithm_tag)" size="small" round>{{ row.algorithm_tag }}</el-tag>
            <span v-else class="text-muted">未标记</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{row}">
            <template v-if="row.status==='待处理'">
              <el-button type="primary" size="small" @click.stop="openTag(row)">标记</el-button>
              <el-button size="small" @click.stop="markIgnore(row)">不考虑</el-button>
            </template>
            <el-button v-else-if="row.status==='待回访'||row.status==='处理中'" type="success" size="small" @click.stop="openHandle(row)">处理</el-button>
            <el-button v-if="row.status!=='已归档'&&row.status!=='已完成'" size="small" @click.stop="openNote(row)" text>备注</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev,pager,next" @current-change="loadRecords" style="margin-top:16px;justify-content:flex-end" />
    </el-card>

    <!-- Tag dialog -->
    <el-dialog v-model="tagVisible" title="算法标记" width="450px" destroy-on-close>
      <div class="dialog-info"><strong>{{ cur?.institution }} - {{ cur?.person_name }}</strong><br/><span class="text-muted">{{ cur?.anomaly_type }}: {{ cur?.anomaly_detail }}</span></div>
      <el-form label-width="80px" style="margin-top:12px">
        <el-form-item label="标记" required><el-radio-group v-model="tagF.tag"><el-radio value="需要回访">需要回访</el-radio><el-radio value="算法问题">算法问题</el-radio><el-radio value="真实案例">真实案例</el-radio></el-radio-group></el-form-item>
        <el-form-item label="备注"><el-input v-model="tagF.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="tagVisible=false">取消</el-button><el-button type="primary" @click="doTag" :loading="tagging">确认</el-button></template>
    </el-dialog>

    <!-- Handle dialog -->
    <el-dialog v-model="handleVisible" title="处理工单" width="450px" destroy-on-close>
      <div class="dialog-info"><strong>{{ cur?.institution }} - {{ cur?.person_name }}</strong><br/><span class="text-muted">{{ cur?.anomaly_type }}: {{ cur?.anomaly_detail }}</span><br/><el-tag v-if="cur?.algorithm_tag" :type="tagColor(cur?.algorithm_tag)" size="small" round>{{ cur?.algorithm_tag }}</el-tag></div>
      <el-form label-width="80px" style="margin-top:12px">
        <el-form-item label="处理结果" required><el-input v-model="handleF.resolution" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="handleF.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="handleVisible=false">取消</el-button><el-button type="primary" @click="doHandle" :loading="handling">确认完成</el-button></template>
    </el-dialog>

    <!-- Note dialog -->
    <el-dialog v-model="noteVisible" title="添加备注" width="400px" destroy-on-close>
      <el-input v-model="newNote" type="textarea" :rows="3" />
      <template #footer><el-button @click="noteVisible=false">取消</el-button><el-button type="primary" @click="doNote" :loading="noting">添加</el-button></template>
    </el-dialog>

    <!-- Detail dialog -->
    <el-dialog v-model="detailVisible" title="工单详情" width="600px" destroy-on-close>
      <template v-if="cur">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="日期">{{ cur.record_date }}</el-descriptions-item>
          <el-descriptions-item label="机构">{{ cur.institution }}</el-descriptions-item>
          <el-descriptions-item label="老人">{{ cur.person_name }}</el-descriptions-item>
          <el-descriptions-item label="设备号">{{ cur.device_id }}</el-descriptions-item>
          <el-descriptions-item label="异常类型">{{ cur.anomaly_type }}</el-descriptions-item>
          <el-descriptions-item label="优先级"><el-tag :type="cur.priority==='高'?'danger':'warning'" size="small" round>{{ cur.priority }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="详情" :span="2">{{ cur.anomaly_detail }}</el-descriptions-item>
          <el-descriptions-item label="标记">{{ cur.algorithm_tag || '未标记' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ cur.status }}</el-descriptions-item>
          <el-descriptions-item label="处理结果" :span="2">{{ cur.resolution || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin-top:14px">操作时间线</h4>
        <el-timeline v-if="timeline.length" style="margin-top:8px">
          <el-timeline-item v-for="a in timeline" :key="a.id" :timestamp="fmt(a.created_at)"><strong>{{ a.action_by }}</strong> {{ a.action_type }}: {{ a.content }}</el-timeline-item>
        </el-timeline>
        <p v-else class="text-muted">暂无记录</p>
      </template>
    </el-dialog>

    <!-- Ignore list dialog -->
    <el-dialog v-model="showIgnoreList" title="不考虑列表" width="650px" destroy-on-close @opened="loadIgnoreRules">
      <el-table :data="ignoreRules" stripe size="small">
        <el-table-column prop="device_id" label="设备号" width="150" />
        <el-table-column prop="anomaly_type" label="异常类型" width="120" />
        <el-table-column prop="reason" label="原因" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_by" label="操作人" width="80" />
        <el-table-column prop="created_at" label="时间" width="140" />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{row}">
            <el-button size="small" type="danger" text @click="removeIgnore(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!ignoreRules.length" description="暂无忽略规则" />
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { opsAPI } from '../api/index.js'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })
api.interceptors.request.use(c => { c.headers.Authorization = `Bearer ${localStorage.getItem('access_token')}`; return c })
api.interceptors.response.use(r => r.data)

export default {
  name: 'AnomalyTickets',
  setup() {
    const loading=ref(false),syncing=ref(false),records=ref([]),total=ref(0),page=ref(1),pageSize=ref(20)
    const stats=ref({}),activeStatus=ref('待处理'),filterDate=ref(''),filterInst=ref(''),filterType=ref(''),searchText=ref('')
    const allInstitutions=ref([])
    const statusList=[{key:'待处理',label:'待处理',color:'#f5222d'},{key:'处理中',label:'处理中',color:'#fa8c16'},{key:'待回访',label:'待回访',color:'#1a73e8'},{key:'已完成',label:'已完成',color:'#52c41a'},{key:'已归档',label:'已归档',color:'#8c8c8c'}]

    const tagVisible=ref(false),handleVisible=ref(false),noteVisible=ref(false),detailVisible=ref(false)
    const cur=ref(null),tagging=ref(false),handling=ref(false),noting=ref(false)
    const tagF=reactive({tag:'',notes:''}),handleF=reactive({resolution:'',notes:''}),newNote=ref(''),timeline=ref([])

    const showIgnoreList=ref(false),ignoreRules=ref([])

    const fmt=t=>t?t.replace('T',' ').substring(0,16):'-'
    const statusColor=s=>({待处理:'danger',处理中:'warning',待回访:'',已完成:'success',已归档:'info'}[s]||'info')
    const tagColor=t=>({需要回访:'warning',算法问题:'',真实案例:'success'}[t]||'info')

    const loadStats=async()=>{
      try{const r=await opsAPI.getAnomalyStats();if(r.success)stats.value=r.stats}catch{/*ignore*/}
    }
    const loadRecords=async()=>{
      loading.value=true
      try{
        const p={status:activeStatus.value,skip:(page.value-1)*pageSize.value,limit:pageSize.value}
        if(filterDate.value)p.record_date=filterDate.value
        if(filterInst.value)p.institution=filterInst.value
        if(filterType.value)p.anomaly_type=filterType.value
        if(searchText.value)p.search=searchText.value
        const r=await opsAPI.getAnomalyRecords(p)
        records.value=r.items||[]; total.value=r.total||0
        // Collect all institutions from separate call
        try{const all=await opsAPI.getAnomalyRecords({limit:10000});const s=new Set();(all.items||[]).forEach(x=>{if(x.institution)s.add(x.institution)});allInstitutions.value=[...s].sort()}catch{}
      }catch(e){ElMessage.error('加载失败')}
      finally{loading.value=false}
    }
    const switchStatus=k=>{activeStatus.value=k;page.value=1;loadRecords()}
    const onDateFilter=()=>{page.value=1;loadRecords()}

    const syncNow=async()=>{
      syncing.value=true
      try{const r=await opsAPI.syncAnomalyData(filterDate.value||new Date().toISOString().slice(0,10));if(r.success){ElMessage.success(`同步完成,新增${r.inserted_records}条`);await loadStats();await loadRecords()}else ElMessage.error(r.detail||'同步失败')}
      catch(e){ElMessage.error('同步失败: '+(e.response?.data?.detail||e.message))}
      finally{syncing.value=false}
    }

    const exportExcel=async()=>{
      try{
        const date=filterDate.value||new Date().toISOString().slice(0,10)
        const r=await axios.get('/operations/sync/export-report',{params:{date},responseType:'blob'})
        if(r.type==='application/json'){const t=await r.text();try{const j=JSON.parse(t);if(!j.success){ElMessage.error(j.detail||'导出失败');return}}catch{}}
        const url=URL.createObjectURL(new Blob([r],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}))
        const a=document.createElement('a');a.href=url;a.download=`异常汇总_${date}.xlsx`;a.click();URL.revokeObjectURL(url);ElMessage.success('下载成功')
      }catch(e){ElMessage.error('导出失败，请先同步数据')}
    }

    const openTag=r=>{cur.value=r;tagF.tag='';tagF.notes='';tagVisible.value=true}
    const doTag=async()=>{
      if(!tagF.tag){ElMessage.warning('请选择标记');return}
      tagging.value=true
      try{await opsAPI.tagAnomaly(cur.value.id,{algorithm_tag:tagF.tag,algorithm_notes:tagF.notes});ElMessage.success('已标记');tagVisible.value=false;await loadStats();await loadRecords()}
      catch(e){ElMessage.error('标记失败')}
      finally{tagging.value=false}
    }

    const markIgnore=async(r)=>{
      try{
        await opsAPI.tagAnomaly(r.id,{algorithm_tag:'算法问题',algorithm_notes:'标记为不考虑'})
        await api.post('/operations/anomaly-ignore-rules',{device_id:r.device_id,anomaly_type:r.anomaly_type,reason:'人工标记不考虑'})
        ElMessage.success('已标记为不考虑，后续不再产生提醒');await loadStats();await loadRecords()
      }catch(e){ElMessage.error('操作失败')}
    }

    const openHandle=r=>{cur.value=r;handleF.resolution='';handleF.notes='';handleVisible.value=true}
    const doHandle=async()=>{
      if(!handleF.resolution){ElMessage.warning('请填写处理结果');return}
      handling.value=true
      try{await opsAPI.handleAnomaly(cur.value.id,{resolution:handleF.resolution,notes:handleF.notes});ElMessage.success('处理完成');handleVisible.value=false;await loadStats();await loadRecords()}
      catch(e){ElMessage.error('处理失败')}
      finally{handling.value=false}
    }

    const openNote=r=>{cur.value=r;newNote.value='';noteVisible.value=true}
    const doNote=async()=>{
      if(!newNote.value.trim()){ElMessage.warning('请输入内容');return}
      noting.value=true
      try{await opsAPI.addAnomalyNote(cur.value.id,{content:newNote.value});ElMessage.success('已添加');noteVisible.value=false}
      catch(e){ElMessage.error('添加失败')}
      finally{noting.value=false}
    }

    const openDetail=async(r)=>{cur.value=r;timeline.value=[];try{const rr=await opsAPI.getAnomalyTimeline(r.id);timeline.value=rr.actions||[]}catch{}detailVisible.value=true}

    const loadIgnoreRules=async()=>{
      try{const r=await api.get('/operations/anomaly-ignore-rules');ignoreRules.value=r.rules||[]}catch{}
    }
    const removeIgnore=async(row)=>{
      try{await api.delete(`/operations/anomaly-ignore-rules/${row.id}`);ElMessage.success('已移除，设备恢复产生工单');await loadIgnoreRules()}
      catch(e){ElMessage.error('移除失败')}
    }

    onMounted(async()=>{await Promise.all([loadStats(),loadRecords()])})

    return {loading,syncing,records,total,page,pageSize,stats,activeStatus,statusList,filterDate,filterInst,filterType,searchText,allInstitutions,switchStatus,onDateFilter,loadRecords,syncNow,exportExcel,tagVisible,handleVisible,noteVisible,detailVisible,cur,tagging,handling,noting,tagF,handleF,newNote,timeline,openTag,doTag,markIgnore,openHandle,doHandle,openNote,doNote,openDetail,fmt,statusColor,tagColor,showIgnoreList,ignoreRules,loadIgnoreRules,removeIgnore}
  }
}
</script>

<style scoped>
.anomaly-page { padding: 0; }
.ops-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.ops-toolbar-left, .ops-toolbar-right { display: flex; align-items: center; gap: 8px; }
.kpi-row { margin-bottom: 14px; }
.kpi-card.small { padding: 14px; }
.kpi-card.small .kpi-value { font-size: 24px; }
.kpi-card.active { border: 2px solid #1a73e8; background: #f0f5ff; }
.dialog-info { padding: 8px 0; }
.text-muted { color: #bfbfbf; }
</style>
