<template>
  <div class="reports-page">
    <el-tabs v-model="tab" @tab-change="onTabChange">
      <!-- Daily Report -->
      <el-tab-pane label="日报" name="daily">
        <div class="ops-toolbar">
          <el-date-picker v-model="dailyDate" type="date" value-format="YYYY-MM-DD" size="default" />
          <el-button type="primary" size="default" @click="loadDaily"><el-icon><Search /></el-icon> 查看</el-button>
          <el-button size="default" @click="genDaily" :loading="genDLoading"><el-icon><Refresh /></el-icon> 生成</el-button>
        </div>
        <div v-if="daily" v-loading="dLoading">
          <el-row :gutter="14" class="kpi-row">
            <el-col :span="4"><div class="kpi-card green"><div class="kpi-value">{{ daily.device_online_rate }}%</div><div class="kpi-label">在线率</div></div></el-col>
            <el-col :span="4"><div class="kpi-card blue"><div class="kpi-value">{{ daily.total_monitored_devices }}</div><div class="kpi-label">监控设备</div></div></el-col>
            <el-col :span="4"><div class="kpi-card orange"><div class="kpi-value">{{ daily.new_anomalies }}</div><div class="kpi-label">新增异常</div></div></el-col>
            <el-col :span="4"><div class="kpi-card red"><div class="kpi-value">{{ daily.offline_count }}</div><div class="kpi-label">离线设备</div></div></el-col>
            <el-col :span="4"><div class="kpi-card green"><div class="kpi-value">{{ daily.resolved_count }}</div><div class="kpi-label">已处理</div></div></el-col>
            <el-col :span="4"><div class="kpi-card blue"><div class="kpi-value">{{ daily.new_offline_incidents }}</div><div class="kpi-label">离线事件</div></div></el-col>
          </el-row>
          <el-card shadow="never"><template #header><strong>日报摘要</strong></template><pre class="summary">{{ daily.summary_text }}</pre></el-card>
        </div>
        <el-empty v-else description="暂无日报，请先生成" />
      </el-tab-pane>

      <!-- Weekly Report -->
      <el-tab-pane label="周报" name="weekly">
        <div class="ops-toolbar">
          <el-date-picker v-model="weekStart" type="date" placeholder="选择周一" value-format="YYYY-MM-DD" size="default" />
          <el-button type="primary" size="default" @click="loadWeekly"><el-icon><Search /></el-icon> 查看</el-button>
          <el-button size="default" @click="genWeekly" :loading="genWLoading"><el-icon><Refresh /></el-icon> 生成</el-button>
        </div>
        <div v-if="weekly" v-loading="wLoading">
          <el-row :gutter="14" class="kpi-row">
            <el-col :span="6"><div class="kpi-card orange"><div class="kpi-value">{{ weekly.total_anomalies }}</div><div class="kpi-label">本周异常</div></div></el-col>
            <el-col :span="6"><div class="kpi-card green"><div class="kpi-value">{{ weekly.resolved_count }}</div><div class="kpi-label">已处理</div></div></el-col>
            <el-col :span="6"><div class="kpi-card blue"><div class="kpi-value">{{ weekly.resolution_rate }}%</div><div class="kpi-label">处理率</div></div></el-col>
            <el-col :span="6"><div class="kpi-card red"><div class="kpi-value">{{ weekly.total_anomalies - weekly.resolved_count }}</div><div class="kpi-label">剩余未处理</div></div></el-col>
          </el-row>
          <el-row :gutter="14">
            <el-col :span="12">
              <el-card shadow="never"><template #header><strong>机构异常 TOP10</strong></template>
                <div v-for="(it,idx) in tops" :key="idx" class="rank-row">
                  <span class="rank-num">{{ idx+1 }}</span><span class="rank-name">{{ it.name }}</span>
                  <el-progress :percentage="tops.length?Math.round(it.count/tops[0].count*100):0" :show-text="false" :stroke-width="6" style="flex:1;margin:0 10px" />
                  <span class="rank-count">{{ it.count }}例</span>
                </div>
                <el-empty v-if="!tops.length" description="暂无" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never"><template #header><strong>高频异常设备</strong></template>
                <div v-for="(it,idx) in topDevs" :key="idx" class="rank-row">
                  <span class="rank-num">{{ idx+1 }}</span><span class="rank-name">{{ it.device_id }}</span><span class="rank-count">{{ it.count }}次</span>
                </div>
                <el-empty v-if="!topDevs.length" description="暂无" />
              </el-card>
            </el-col>
          </el-row>
        </div>
        <el-empty v-else description="暂无周报，请先生成" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { opsAPI } from '../api/index.js'

export default {
  name: 'OpsReports',
  setup() {
    const tab=ref('daily'),dailyDate=ref(new Date().toISOString().slice(0,10)),daily=ref(null),dLoading=ref(false),genDLoading=ref(false)
    const weekStart=ref(getMonday()),weekly=ref(null),wLoading=ref(false),genWLoading=ref(false),tops=ref([]),topDevs=ref([])

    function getMonday(){const d=new Date();d.setDate(d.getDate()-((d.getDay()+6)%7));return d.toISOString().slice(0,10)}

    const loadDaily=async()=>{dLoading.value=true;try{const r=await opsAPI.getDailyReport(dailyDate.value);daily.value=r.has_report?r.report:null;if(!r.has_report)ElMessage.info('该日期暂无日报')}catch(e){ElMessage.error('加载失败')}finally{dLoading.value=false}}
    const genDaily=async()=>{genDLoading.value=true;try{const r=await opsAPI.generateDailyReport(dailyDate.value);if(r.success){daily.value=r.report;ElMessage.success('日报已生成')}else ElMessage.error(r.detail||'生成失败')}catch(e){ElMessage.error('生成失败')}finally{genDLoading.value=false}}

    const loadWeekly=async()=>{wLoading.value=true;try{const r=await opsAPI.getWeeklyReport(weekStart.value);if(r.has_report){weekly.value=r.report;tops.value=r.report.top_institutions||[];topDevs.value=r.report.top_devices||[]}else{weekly.value=null;ElMessage.info('该周暂无周报')}}catch(e){ElMessage.error('加载失败')}finally{wLoading.value=false}}
    const genWeekly=async()=>{genWLoading.value=true;try{const r=await opsAPI.generateWeeklyReport(weekStart.value);if(r.success){weekly.value=r.report;tops.value=r.report.top_institutions||[];topDevs.value=r.report.top_devices||[];ElMessage.success('周报已生成')}else ElMessage.error(r.detail||'生成失败')}catch(e){ElMessage.error('生成失败')}finally{genWLoading.value=false}}

    const onTabChange=t=>{if(t==='daily')loadDaily();else loadWeekly()}
    onMounted(()=>loadDaily())

    return {tab,dailyDate,daily,dLoading,genDLoading,loadDaily,genDaily,weekStart,weekly,wLoading,genWLoading,tops,topDevs,loadWeekly,genWeekly,onTabChange}
  }
}
</script>

<style scoped>
.reports-page { padding: 0; }
.ops-toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 14px; }
.kpi-row { margin-bottom: 14px; }
.summary { white-space: pre-wrap; font-size: 14px; line-height: 2; color: #303133; background: #fafafa; padding: 16px; border-radius: 8px; }
.rank-row { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid #f5f5f5; }
.rank-row:last-child { border-bottom: none; }
.rank-num { width: 22px; height: 22px; border-radius: 50%; background: #1a73e8; color: #fff; font-size: 11px; display: flex; align-items: center; justify-content: center; margin-right: 8px; flex-shrink: 0; }
.rank-name { font-size: 13px; min-width: 100px; }
.rank-count { font-size: 12px; color: #8c8c8c; margin-left: 8px; }
</style>
