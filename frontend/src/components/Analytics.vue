<template>
  <div class="analytics" v-loading="loading">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409EFF;">
              <el-icon><Box /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalDevices }}</div>
              <div class="stat-label">设备总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67C23A;">
              <el-icon><ShoppingCart /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.soldDevices }}</div>
              <div class="stat-label">已售设备</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #E6A23C;">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.trialDevices }}</div>
              <div class="stat-label">试用设备</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #909399;">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.stockDevices }}</div>
              <div class="stat-label">库存设备</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts">
      <!-- 设备属性分布 -->
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>
            <div class="chart-header">
              <span>设备属性分布</span>
            </div>
          </template>
          <div ref="attributeChart" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- 版本与类型分布 -->
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>
            <div class="chart-header">
              <span>版本与类型分布</span>
            </div>
          </template>
          <div ref="typeVersionChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts">
      <!-- 机构销售统计 -->
      <el-col :xs="24">
        <el-card>
          <template #header>
            <div class="chart-header">
              <span>机构销售统计</span>
              <el-button size="small" @click="loadData" style="margin-left: 10px;">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
          </template>
          <div ref="institutionChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细数据表格 -->
    <el-row :gutter="20" class="details">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>机构销售明细</span>
          </template>
          <el-table :data="institutionDetails" border stripe>
            <el-table-column prop="owner" label="机构名称" width="200"></el-table-column>
            <el-table-column prop="count" label="设备数量" width="120" align="center"></el-table-column>
            <el-table-column prop="percentage" label="占比" width="100" align="center">
              <template #default="{ row }">
                {{ row.percentage }}%
              </template>
            </el-table-column>
            <el-table-column prop="deviceIds" label="设备列表" min-width="300">
              <template #default="{ row }">
                <el-tag v-for="id in row.deviceIds" :key="id" size="small" style="margin: 2px;">
                  {{ id }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- AI分析查询 -->
    <el-row :gutter="20" class="charts" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="chart-header">
              <span>AI 智能分析</span>
            </div>
          </template>
          <div style="display: flex; gap: 12px; margin-bottom: 16px;">
            <el-input v-model="analysisQuery" placeholder="输入你的分析问题，例如：大家保险一共拿走了多少台设备？"
              style="flex: 1" @keyup.enter="runAnalysis" />
            <el-button type="primary" @click="runAnalysis" :loading="analyzing">分析</el-button>
            <el-button @click="loadWeeklyReport" :loading="weekLoading">本周报告</el-button>
          </div>
          <div v-if="analysisResult" style="padding: 16px; background: #f5f7fa; border-radius: 8px; white-space: pre-wrap;">
            {{ analysisResult }}
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';
import * as echarts from 'echarts';
import { inventoryAPI, analysisAPI } from '../api';
import { ElMessage } from 'element-plus';
import { Box, ShoppingCart, User, Document, Refresh } from '@element-plus/icons-vue';

export default {
  name: 'Analytics',
  components: { Box, ShoppingCart, User, Document, Refresh },
  setup() {
    const loading = ref(false);
    const stats = ref({
      totalDevices: 0,
      soldDevices: 0,
      trialDevices: 0,
      stockDevices: 0
    });
    
    const institutionDetails = ref([]);
    
    const attributeChart = ref(null);
    const typeVersionChart = ref(null);
    const institutionChart = ref(null);
    
    let attributeChartInstance = null;
    let typeVersionChartInstance = null;
    let institutionChartInstance = null;
    let handleResizeFn = null;

    // 加载数据
    const loadData = async () => {
      loading.value = true;
      try {
        // 获取所有设备
        const response = await inventoryAPI.getAll({ skip: 0, limit: 10000 });
        const devices = response.items || response;
        const total = response.total || devices.length;
        
        // 统计数据
        let soldCount = 0;
        let trialCount = 0;
        let stockCount = 0;
        const attributeCount = {};
        const versionCount = {};
        const typeCount = {};
        const institutionData = {};
        
        devices.forEach(device => {
          // 统计设备属性
          const attr = device.device_attribute || '未分类';
          attributeCount[attr] = (attributeCount[attr] || 0) + 1;
          
          // 统计版本
          const ver = device.version || '未分类';
          versionCount[ver] = (versionCount[ver] || 0) + 1;
          
          // 统计类型
          const type = device.type || '未分类';
          typeCount[type] = (typeCount[type] || 0) + 1;
          
          // 统计售卖（含已售出和组织售卖）
          if (device.device_attribute === '组织售卖' || device.device_attribute === '已售出') {
            soldCount++;
            const owner = device.owner || '未指定';
            if (!institutionData[owner]) {
              institutionData[owner] = [];
            }
            institutionData[owner].push(device.device_id);
          }
          
          // 统计试用
          if (device.device_attribute === '商机试用') {
            trialCount++;
          }
          
          // 统计库存
          if (device.device_attribute === '现有库存') {
            stockCount++;
          }
        });
        
        stats.value = {
          totalDevices: total,
          soldDevices: soldCount,
          trialDevices: trialCount,
          stockDevices: stockCount
        };
        
        // 更新机构明细
        institutionDetails.value = Object.entries(institutionData).map(([owner, deviceIds]) => ({
          owner,
          count: deviceIds.length,
          percentage: soldCount > 0 ? ((deviceIds.length / soldCount) * 100).toFixed(1) : 0,
          deviceIds
        })).sort((a, b) => b.count - a.count);
        
        // 更新图表
        updateAttributeChart(attributeCount);
        updateTypeVersionChart(versionCount, typeCount);
        updateInstitutionChart(institutionData);
        
      } catch (error) {
        console.error('加载数据失败:', error);
        ElMessage.error('加载统计数据失败');
      } finally {
        loading.value = false;
      }
    };

    // 更新设备属性分布图
    const updateAttributeChart = (attributeCount) => {
      if (!attributeChartInstance) return;
      
      const data = Object.entries(attributeCount).map(([name, value]) => ({ name, value }));
      
      attributeChartInstance.setOption({
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c}台 ({d}%)'
        },
        legend: {
          orient: 'vertical',
          left: 'left'
        },
        series: [{
          name: '设备属性',
          type: 'pie',
          radius: '60%',
          data: data,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          label: {
            formatter: '{b}\n{c}台 ({d}%)'
          }
        }],
        color: ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#C0C4CC']
      });
    };

    // 更新版本与类型分布图
    const updateTypeVersionChart = (versionCount, typeCount) => {
      if (!typeVersionChartInstance) return;
      
      typeVersionChartInstance.setOption({
        tooltip: {
          trigger: 'item'
        },
        legend: {
          top: '5%',
          left: 'center'
        },
        series: [
          {
            name: '版本',
            type: 'pie',
            radius: ['0%', '40%'],
            label: {
              formatter: '{b}: {c}台'
            },
            data: Object.entries(versionCount).map(([name, value]) => ({ name, value }))
          },
          {
            name: '类型',
            type: 'pie',
            radius: ['50%', '70%'],
            label: {
              formatter: '{b}: {c}台'
            },
            data: Object.entries(typeCount).map(([name, value]) => ({ name, value }))
          }
        ],
        color: ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C']
      });
    };

    // 更新机构销售图
    const updateInstitutionChart = (institutionData) => {
      if (!institutionChartInstance) return;
      
      const institutions = Object.keys(institutionData);
      const counts = Object.values(institutionData).map(ids => ids.length);
      
      institutionChartInstance.setOption({
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: institutions,
          axisTick: {
            alignWithLabel: true
          }
        },
        yAxis: {
          type: 'value',
          name: '设备数量(台)'
        },
        series: [{
          name: '设备数量',
          type: 'bar',
          barWidth: '60%',
          data: counts,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#83bff6' },
              { offset: 0.5, color: '#188df0' },
              { offset: 1, color: '#188df0' }
            ])
          },
          label: {
            show: true,
            position: 'top',
            formatter: '{c}台'
          }
        }]
      });
    };

    onMounted(async () => {
      // 初始化图表
      attributeChartInstance = echarts.init(attributeChart.value);
      typeVersionChartInstance = echarts.init(typeVersionChart.value);
      institutionChartInstance = echarts.init(institutionChart.value);
      
      // 加载数据
      await loadData();
      
      // 监听窗口大小变化
      handleResizeFn = () => {
        if (attributeChartInstance) attributeChartInstance.resize();
        if (typeVersionChartInstance) typeVersionChartInstance.resize();
        if (institutionChartInstance) institutionChartInstance.resize();
      };
      window.addEventListener('resize', handleResizeFn);
    });

    onUnmounted(() => {
      if (handleResizeFn) window.removeEventListener('resize', handleResizeFn);
      if (attributeChartInstance) attributeChartInstance.dispose();
      if (typeVersionChartInstance) typeVersionChartInstance.dispose();
      if (institutionChartInstance) institutionChartInstance.dispose();
    });

    const analysisQuery = ref('');
    const analysisResult = ref('');
    const analyzing = ref(false);
    const weekLoading = ref(false);

    const runAnalysis = async () => {
      if (!analysisQuery.value.trim() || analyzing.value) return;
      analyzing.value = true;
      analysisResult.value = '';
      try {
        const res = await analysisAPI.query({ query: analysisQuery.value });
        analysisResult.value = res.answer || res.data?.summary || '分析完成';
      } catch (e) {
        ElMessage.error('分析查询失败');
      } finally {
        analyzing.value = false;
      }
    };

    const loadWeeklyReport = async () => {
      weekLoading.value = true;
      try {
        const res = await analysisAPI.getWeeklyReport();
        const lines = [`本周（${res.period}）出库统计：`, `总出库: ${res.total_outbound} 台`];
        (res.by_attribute || []).forEach(a => lines.push(`  ${a.name}: ${a.count} 台`));
        lines.push('', '按型号：');
        (res.by_version || []).forEach(v => lines.push(`  ${v.name}: ${v.count} 台`));
        analysisResult.value = lines.join('\n');
      } catch (e) {
        ElMessage.error('加载周报失败');
      } finally {
        weekLoading.value = false;
      }
    };

    return {
      loading,
      stats,
      institutionDetails,
      attributeChart,
      typeVersionChart,
      institutionChart,
      loadData,
      analysisQuery,
      analysisResult,
      analyzing,
      weekLoading,
      runAnalysis,
      loadWeeklyReport
    };
  }
};
</script>

<style scoped>
.analytics {
  padding: 20px;
}

.stats-cards {
  margin-bottom: 20px;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  padding: 10px 0;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.stat-icon .el-icon {
  font-size: 30px;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.charts {
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.details {
  margin-top: 20px;
}
</style>
