<template>
  <div class="daily-ops">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- ========== Tab 1: 每日运营分析 ========== -->
      <el-tab-pane label="每日运营分析" name="analysis">
        <div class="tab-header">
          <div class="date-selector">
            <span class="label">选择日期：</span>
            <el-date-picker
              v-model="selectedDate"
              type="date"
              placeholder="选择日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :disabled-date="disabledDate"
            />
          </div>
          <div class="actions">
            <el-button type="primary" @click="runDownload" :loading="downloading">
              <el-icon><Download /></el-icon> 下载数据
            </el-button>
            <el-button type="warning" @click="runAnalysis" :loading="analyzing" :disabled="!hasData">
              <el-icon><Search /></el-icon> 运行分析
            </el-button>
            <el-button type="success" @click="runFullPipeline" :loading="fullRunning">
              <el-icon><CircleCheck /></el-icon> 一键执行
            </el-button>
          </div>
        </div>

        <!-- 历史日期 -->
        <div class="available-dates" v-if="availableDates.length > 0">
          <span class="label">已有数据日期：</span>
          <el-tag
            v-for="d in availableDates.slice(0, 14)"
            :key="d"
            :type="d === selectedDate ? 'success' : 'info'"
            class="date-tag"
            @click="selectDate(d)"
          >
            {{ d }}
          </el-tag>
        </div>

        <!-- 执行日志 -->
        <div v-if="logs.length > 0" class="log-panel">
          <div class="log-header">
            <span>执行日志</span>
            <el-button type="danger" link size="small" @click="logs = []">清空</el-button>
          </div>
          <div v-for="(log, i) in logs" :key="i" class="log-line" :class="log.type">
            {{ log.text }}
          </div>
        </div>

        <!-- 无报告提示 -->
        <el-alert
          v-if="reportStatus === 'none'"
          type="warning"
          :closable="false"
          show-icon
          style="margin-top: 12px;"
        >
          <template #title>
            {{ selectedDate }} 尚未生成分析报告，请先点击「一键执行」下载数据并分析。
          </template>
        </el-alert>

        <!-- 分析结果 -->
        <div v-if="reportStatus === 'ok' && report" class="report-section">
          <el-divider />
          <div class="report-content">
            <!-- 摘要文本 -->
            <el-card class="summary-card">
              <template #header><span>{{ selectedDate }} 汇总报告</span></template>
              <pre class="summary-text">{{ report.summary_text }}</pre>
            </el-card>

            <!-- 统计卡片 -->
            <el-row :gutter="16" class="stats-row" v-if="report.stats">
              <el-col :span="6">
                <el-statistic title="有效设备" :value="report.stats.valid_devices" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="异常设备" :value="report.stats.abnormal_devices" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="异常汇总" :value="report.stats.total_summary" />
              </el-col>
              <el-col :span="6">
                <el-statistic title="状态变化" :value="report.stats.status_changes" />
              </el-col>
            </el-row>

            <!-- 分类统计 -->
            <el-card class="breakdown-card" v-if="report.stats">
              <template #header><span>异常分类统计</span></template>
              <el-row :gutter="12">
                <el-col :span="6">
                  <div class="breakdown-item sleep-too-little">
                    <div class="breakdown-num">{{ report.stats.sleep_too_little }}</div>
                    <div class="breakdown-label">睡眠过少</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="breakdown-item bed-exit">
                    <div class="breakdown-num">{{ report.stats.multiple_bed_exit }}</div>
                    <div class="breakdown-label">多次离床</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="breakdown-item sleep-abnormal">
                    <div class="breakdown-num">{{ report.stats.sleep_abnormal }}</div>
                    <div class="breakdown-label">睡眠状态异常</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="breakdown-item vital-abnormal">
                    <div class="breakdown-num">{{ report.stats.vital_abnormal }}</div>
                    <div class="breakdown-label">体征异常</div>
                  </div>
                </el-col>
              </el-row>
            </el-card>

            <!-- 输出文件 -->
            <el-alert
              v-if="report.output_file"
              type="success"
              :closable="false"
              show-icon
              style="margin-top: 12px;"
            >
              报告已生成：{{ report.output_file }}
            </el-alert>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== Tab 2: 设备状态运维（预留窗口） ========== -->
      <el-tab-pane label="设备状态运维" name="status">
        <div class="tab-header">
          <div class="date-selector">
            <span class="label">选择日期：</span>
            <el-date-picker
              v-model="statusDate"
              type="date"
              placeholder="选择日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :disabled-date="disabledDate"
            />
          </div>
          <div class="actions">
            <el-button type="primary" @click="loadDeviceStatus" :loading="loadingStatus">
              <el-icon><Refresh /></el-icon> 查询状态
            </el-button>
          </div>
        </div>

        <!-- 机构统计 -->
        <el-row :gutter="16" class="stats-row" v-if="deviceStatusList.length > 0">
          <el-col :span="6">
            <el-statistic title="设备总数" :value="deviceStatusList.length" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="正常设备" :value="normalDeviceCount" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="异常设备" :value="deviceStatusList.length - normalDeviceCount" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="涉及机构" :value="Object.keys(instStats).length" />
          </el-col>
        </el-row>

        <!-- 设备状态表格 -->
        <div v-if="deviceStatusList.length > 0" style="margin-top: 16px;">
          <div style="margin-bottom: 12px; display: flex; gap: 12px; align-items: center;">
            <el-input v-model="statusFilter" placeholder="搜索设备号或姓名" clearable style="width: 240px;" />
            <el-select v-model="statusTypeFilter" placeholder="设备状态" clearable style="width: 160px;">
              <el-option label="正常" value="正常" />
              <el-option label="长期卧床" value="长期卧床" />
              <el-option label="长期无人" value="长期无人" />
              <el-option label="睡眠时间断电" value="睡眠时间断电" />
            </el-select>
            <el-select v-model="instFilter" placeholder="机构筛选" clearable style="width: 200px;" filterable>
              <el-option v-for="inst in Object.keys(instStats)" :key="inst" :label="inst" :value="inst" />
            </el-select>
          </div>

          <el-table :data="filteredDevices" stripe border max-height="500" size="small">
            <el-table-column prop="device_id" label="设备号" width="150" fixed />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="institution" label="机构" width="160" />
            <el-table-column prop="status" label="设备状态" width="140">
              <template #default="{ row }">
                <el-tag :type="row.status === '正常' ? 'success' : 'warning'">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sleep_duration" label="睡眠时长(小时)" width="140" sortable />
            <el-table-column prop="bed_exit_count" label="离床次数" width="100" sortable />
          </el-table>
        </div>

        <!-- 预留说明 -->
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-top: 16px;"
        >
          <template #title>
            此窗口为设备每日状态运维预留。当前从本地 Excel 数据读取，后续可直接连接数据库实时查询设备状态，支持按机构、状态筛选，并可扩展异常标记、运维记录等功能。
          </template>
        </el-alert>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { Download, Search, CircleCheck, Refresh } from '@element-plus/icons-vue';
import { dailyOpsAPI } from '../api/index.js';

export default {
  name: 'DailyOps',
  components: { Download, Search, CircleCheck, Refresh },
  setup() {
    const activeTab = ref('analysis');

    // ===== Tab 1: 分析 =====
    const selectedDate = ref(new Date().toISOString().slice(0, 10));
    const downloading = ref(false);
    const analyzing = ref(false);
    const fullRunning = ref(false);
    const logs = ref([]);
    const report = ref(null);
    const reportStatus = ref('none'); // 'none' | 'ok'
    const availableDates = ref([]);
    const hasData = ref(false);

    // ===== Tab 2: 状态 =====
    const statusDate = ref(new Date().toISOString().slice(0, 10));
    const loadingStatus = ref(false);
    const deviceStatusList = ref([]);
    const instStats = ref({});
    const statusFilter = ref('');
    const statusTypeFilter = ref('');
    const instFilter = ref('');

    const normalDeviceCount = computed(() =>
      deviceStatusList.value.filter(d => d.status === '正常').length
    );

    const filteredDevices = computed(() => {
      let list = deviceStatusList.value;
      if (statusFilter.value) {
        const kw = statusFilter.value.toLowerCase();
        list = list.filter(d => d.device_id.toLowerCase().includes(kw) || d.name.toLowerCase().includes(kw));
      }
      if (statusTypeFilter.value) {
        list = list.filter(d => d.status === statusTypeFilter.value);
      }
      if (instFilter.value) {
        list = list.filter(d => d.institution === instFilter.value);
      }
      return list;
    });

    const disabledDate = (time) => time.getTime() > Date.now();

    const addLog = (text, type = 'info') => {
      logs.value.push({ text: `[${new Date().toLocaleTimeString()}] ${text}`, type });
    };

    const loadAvailableDates = async () => {
      try {
        const res = await dailyOpsAPI.getAvailableDates();
        availableDates.value = res.dates || [];
      } catch { /* 静默失败 */ }
    };

    const selectDate = (date) => {
      selectedDate.value = date;
      loadReport(date);
    };

    const loadReport = async (date) => {
      reportStatus.value = 'none';
      report.value = null;
      try {
        const res = await dailyOpsAPI.getReport(date);
        if (res.success && res.has_report) {
          report.value = {
            summary_text: res.summary_text,
            stats: res.stats || null,
            output_file: null,
          };
          reportStatus.value = 'ok';
          hasData.value = true;
        } else {
          report.value = { summary_text: res.summary_text };
          reportStatus.value = 'none';
          hasData.value = false;
        }
      } catch {
        report.value = { summary_text: `加载 ${date} 的报告失败，请检查后端服务。` };
        reportStatus.value = 'none';
      }
    };

    const runDownload = async () => {
      downloading.value = true;
      addLog(`开始下载 ${selectedDate.value} 的数据...`);
      try {
        const res = await dailyOpsAPI.download({ date: selectedDate.value, include_previous: true });
        if (res.success) {
          addLog(`下载完成: 新下载 ${res.downloaded.length} 个, 跳过 ${res.skipped.length} 个`, 'success');
          hasData.value = true;
          await loadAvailableDates();
          ElMessage.success('数据下载完成');
        }
      } catch (e) {
        addLog(`下载失败: ${e.response?.data?.detail || e.message}`, 'error');
        ElMessage.error('数据下载失败');
      } finally {
        downloading.value = false;
      }
    };

    const runAnalysis = async () => {
      analyzing.value = true;
      addLog(`开始分析 ${selectedDate.value} 的数据...`);
      try {
        const res = await dailyOpsAPI.analyze({ date: selectedDate.value });
        if (res.success) {
          report.value = res;
          reportStatus.value = 'ok';
          addLog('分析完成', 'success');
          ElMessage.success('分析完成');
        }
      } catch (e) {
        addLog(`分析失败: ${e.response?.data?.detail || e.message}`, 'error');
        ElMessage.error('分析失败');
      } finally {
        analyzing.value = false;
      }
    };

    const runFullPipeline = async () => {
      fullRunning.value = true;
      addLog(`一键执行: ${selectedDate.value}...`);
      try {
        const res = await dailyOpsAPI.runFull({ date: selectedDate.value });
        if (res.success) {
          report.value = res;
          reportStatus.value = 'ok';
          addLog('一键执行完成', 'success');
          hasData.value = true;
          await loadAvailableDates();
          ElMessage.success('一键执行完成');
        }
      } catch (e) {
        addLog(`执行失败: ${e.response?.data?.detail || e.message}`, 'error');
        ElMessage.error('执行失败');
      } finally {
        fullRunning.value = false;
      }
    };

    const loadDeviceStatus = async () => {
      loadingStatus.value = true;
      try {
        const res = await dailyOpsAPI.getDeviceStatus(statusDate.value);
        if (res.success) {
          deviceStatusList.value = res.devices || [];
          instStats.value = res.institution_stats || {};
          ElMessage.success(`加载了 ${res.total_devices} 台设备状态`);
        }
      } catch (e) {
        ElMessage.error('加载设备状态失败');
      } finally {
        loadingStatus.value = false;
      }
    };

    // 切换 Tab 到状态页时自动加载数据
    watch(activeTab, (val) => {
      if (val === 'status') {
        loadDeviceStatus();
      }
    });

    // 初始化
    loadAvailableDates();
    loadReport(selectedDate.value);

    return {
      activeTab,
      selectedDate, downloading, analyzing, fullRunning,
      logs, report, reportStatus, availableDates, hasData, disabledDate,
      selectDate, runDownload, runAnalysis, runFullPipeline, loadReport,
      statusDate, loadingStatus, deviceStatusList, instStats,
      statusFilter, statusTypeFilter, instFilter,
      normalDeviceCount, filteredDevices, loadDeviceStatus,
    };
  },
};
</script>

<style scoped>
.daily-ops { min-height: 500px; }
.tab-header {
  display: flex; align-items: center; gap: 16px;
  margin-bottom: 16px; flex-wrap: wrap;
}
.date-selector { display: flex; align-items: center; gap: 8px; }
.date-selector .label { font-weight: 500; white-space: nowrap; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.available-dates { margin-bottom: 12px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.available-dates .label { font-weight: 500; font-size: 13px; color: #606266; }
.date-tag { cursor: pointer; }

.log-panel { background: #1e1e1e; color: #d4d4d4; border-radius: 6px; padding: 12px; margin-bottom: 12px; max-height: 200px; overflow-y: auto; font-family: Consolas, monospace; font-size: 13px; }
.log-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; color: #888; }
.log-line { padding: 2px 0; }
.log-line.success { color: #4ec9b0; }
.log-line.error { color: #f44747; }

.report-section { margin-top: 8px; }
.summary-text { white-space: pre-wrap; font-size: 14px; line-height: 1.8; margin: 0; color: #303133; }
.stats-row { margin: 16px 0; }

.breakdown-item {
  text-align: center; padding: 16px; border-radius: 8px;
  background: #f5f7fa;
}
.breakdown-num { font-size: 28px; font-weight: 700; }
.breakdown-label { font-size: 13px; color: #909399; margin-top: 4px; }
.sleep-too-little .breakdown-num { color: #e6a23c; }
.bed-exit .breakdown-num { color: #f56c6c; }
.sleep-abnormal .breakdown-num { color: #909399; }
.vital-abnormal .breakdown-num { color: #e04040; }
</style>
