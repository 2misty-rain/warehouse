<template>
  <div class="dashboard">
    <!-- 标题栏 + 刷新 -->
    <div class="header-row">
      <span class="header-title">仪表盘</span>
      <span class="last-update" v-if="lastUpdate">上次更新: {{ lastUpdate }}</span>
      <el-button size="small" @click="refreshAll" :loading="refreshing" type="primary">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 智能预警区域 -->
    <el-row :gutter="20" class="alerts-row" v-if="alerts.upcomingTrialEnd > 0 || alerts.overdueBorrows > 0 || alerts.longTermBorrows > 0">
      <el-col :span="24">
        <el-alert title="智能预警" type="warning" :closable="false" show-icon>
          <template #default>
            <div class="alert-content">
              <el-tag v-if="alerts.upcomingTrialEnd > 0" type="warning" style="margin-right: 10px;">
                <el-icon><Warning /></el-icon>
                {{ alerts.upcomingTrialEnd }} 个试用设备即将到期（7天内）
              </el-tag>
              <el-tag v-if="alerts.overdueBorrows > 0" type="danger" style="margin-right: 10px;">
                <el-icon><CircleCloseFilled /></el-icon>
                {{ alerts.overdueBorrows }} 个设备逾期未还
              </el-tag>
              <el-tag v-if="alerts.longTermBorrows > 0" type="info">
                <el-icon><Clock /></el-icon>
                {{ alerts.longTermBorrows }} 个设备长期借出（>30天）
              </el-tag>
            </div>
          </template>
        </el-alert>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card>
          <template #header><span>设备类型分布</span></template>
          <div ref="typeChart" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>版本分布</span></template>
          <div ref="versionChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-row">
      <el-col :span="24">
        <el-card>
          <template #header><span>月度销售趋势</span></template>
          <div v-if="!loadingSales && !error" ref="salesChart" class="chart-container"></div>
          <div v-else-if="loadingSales" class="loading">加载中...</div>
          <div v-else class="error">加载失败: {{ error }}</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import * as echarts from 'echarts';
import { onMounted, onUnmounted, ref } from 'vue';
import { dashboardAPI, inventoryAPI, reservationAPI } from '../api';
import { Warning, CircleCloseFilled, Clock, Refresh } from '@element-plus/icons-vue';

export default {
  name: 'Dashboard',
  components: { Warning, CircleCloseFilled, Clock, Refresh },
  setup() {
    const refreshing = ref(false);
    const loadingSales = ref(false);
    const error = ref(null);
    const lastUpdate = ref('');
    const stats = ref([]);
    const alerts = ref({ upcomingTrialEnd: 0, overdueBorrows: 0, longTermBorrows: 0 });

    const typeChart = ref(null);
    const versionChart = ref(null);
    const salesChart = ref(null);
    let typeChartInstance = null;
    let versionChartInstance = null;
    let salesChartInstance = null;

    const loadAll = async () => {
      refreshing.value = true;
      try {
        // 1. 加载统计数据 + 预警
        const data = await dashboardAPI.getStats();
        stats.value = [
          { label: '总设备数', value: data.total_devices, color: '#409EFF' },
          { label: '可用设备', value: data.available_devices, color: '#67C23A' },
          { label: '已售设备', value: data.sold_devices, color: '#E6A23C' },
          { label: '4G开卡数', value: data.active_iot_cards || 0, color: '#67C23A' },
          { label: '待处理提醒', value: data.unprocessed_reminders, color: '#F56C6C' }
        ];
        alerts.value = {
          upcomingTrialEnd: data.upcoming_trial_end || 0,
          overdueBorrows: data.overdue_borrows || 0,
          longTermBorrows: data.long_term_borrows || 0
        };

        // admin 加载待处理预约数
        const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        if (userInfo.role === 'admin') {
          try {
            const r = await reservationAPI.getPendingCount();
            stats.value.push({ label: '待处理预约', value: r.count, color: '#E6A23C' });
          } catch {}
        }

        // 2. 获取所有设备用于动态图表
        const invResp = await inventoryAPI.getAll({ skip: 0, limit: 1000 });
        const devices = invResp.items || invResp;

        // 动态统计类型和版本
        const typeCount = {};
        const versionCount = {};
        devices.forEach(d => {
          const t = d.type || '未分类';
          typeCount[t] = (typeCount[t] || 0) + 1;
          const v = d.version || '未分类';
          versionCount[v] = (versionCount[v] || 0) + 1;
        });

        updateTypeChart(typeCount);
        updateVersionChart(versionCount);

        lastUpdate.value = new Date().toLocaleString();
      } catch (e) {
        console.error('加载数据失败:', e);
      } finally {
        refreshing.value = false;
      }
    };

    const loadSalesTrend = async () => {
      loadingSales.value = true;
      error.value = null;
      try {
        const data = await dashboardAPI.getSalesTrend();
        updateSalesChart(data);
      } catch (err) {
        error.value = '加载销售趋势失败';
        console.error(err);
      } finally {
        loadingSales.value = false;
      }
    };

    const refreshAll = () => {
      loadAll();
      loadSalesTrend();
    };

    const updateTypeChart = (typeCount) => {
      if (!typeChartInstance) return;
      const data = Object.entries(typeCount).map(([name, value]) => ({ name, value }));
      typeChartInstance.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c}台 ({d}%)' },
        legend: { top: '5%', left: 'center' },
        series: [{
          name: '设备类型', type: 'pie', radius: ['40%', '70%'],
          data, label: { formatter: '{b}: {c}台 ({d}%)' },
          emphasis: { label: { fontSize: '18', fontWeight: 'bold' } }
        }]
      });
    };

    const updateVersionChart = (versionCount) => {
      if (!versionChartInstance) return;
      const data = Object.entries(versionCount).map(([name, value]) => ({ name, value }));
      versionChartInstance.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c}台 ({d}%)' },
        legend: { top: '5%', left: 'center' },
        series: [{
          name: '版本', type: 'pie', radius: ['40%', '70%'],
          data, label: { formatter: '{b}: {c}台 ({d}%)' },
          emphasis: { label: { fontSize: '18', fontWeight: 'bold' } }
        }]
      });
    };

    const updateSalesChart = (salesData) => {
      if (!salesChartInstance) return;
      salesChartInstance.setOption({
        title: { text: '月度销售趋势' },
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        toolbox: { feature: { saveAsImage: {} } },
        xAxis: { type: 'category', boundaryGap: false, data: salesData.map(d => d.month) },
        yAxis: { type: 'value', name: '销售数量(台)' },
        series: [{
          name: '已售数量', type: 'line', smooth: true,
          areaStyle: { opacity: 0.15 },
          data: salesData.map(d => d.count),
          itemStyle: { color: '#E6A23C' }
        }]
      });
    };

    let refreshTimer = null;
    const AUTO_REFRESH_INTERVAL = 30000; // 30秒自动刷新

    onMounted(() => {
      typeChartInstance = echarts.init(typeChart.value);
      versionChartInstance = echarts.init(versionChart.value);
      salesChartInstance = echarts.init(salesChart.value);
      loadAll();
      loadSalesTrend();
      // 定时刷新
      refreshTimer = setInterval(refreshAll, AUTO_REFRESH_INTERVAL);
      // 监听AI操作后的数据变更事件
      window.addEventListener('ai-data-changed', refreshAll);
    });

    onUnmounted(() => {
      if (typeChartInstance) typeChartInstance.dispose();
      if (versionChartInstance) versionChartInstance.dispose();
      if (salesChartInstance) salesChartInstance.dispose();
      if (refreshTimer) clearInterval(refreshTimer);
      window.removeEventListener('ai-data-changed', refreshAll);
    });

    return { stats, alerts, refreshing, loadingSales, error, lastUpdate,
             typeChart, versionChart, salesChart, refreshAll };
  }
};
</script>

<style scoped>
.dashboard { padding: 20px; }
.header-row { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
.header-title { font-size: 18px; font-weight: bold; }
.last-update { font-size: 12px; color: #909399; flex: 1; }
.alerts-row { margin-bottom: 20px; }
.alert-content { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; cursor: pointer; transition: transform 0.2s; }
.stat-card:hover { transform: translateY(-5px); }
.stat-content { padding: 20px 0; }
.stat-value { font-size: 26px; font-weight: bold; margin-bottom: 5px; }
.stat-label { font-size: 14px; color: #606266; }
.charts-row { margin-bottom: 20px; }
.chart-container { width: 100%; height: 400px; }
.loading { text-align: center; padding: 40px; color: #909399; }
.error { text-align: center; padding: 40px; color: #F56C6C; }
</style>
