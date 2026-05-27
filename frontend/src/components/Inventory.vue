<template>
  <div class="inventory">
    <!-- 搜索和筛选栏 -->
    <div class="header">
      <el-input
        v-model="searchText"
        placeholder="搜索设备号/归属人..."
        style="width: 300px; margin-right: 10px;"
        clearable
        @input="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select v-model="filterAttribute" placeholder="设备属性" clearable style="width: 150px; margin-right: 10px;" @change="handleSearch">
        <el-option label="现有库存" value="现有库存"></el-option>
        <el-option label="商机交付" value="商机交付"></el-option>
        <el-option label="商机试用" value="商机试用"></el-option>
        <el-option label="内部试用" value="内部试用"></el-option>
        <el-option label="产品演示" value="产品演示"></el-option>
        <el-option label="技术开发/测试" value="技术开发/测试"></el-option>
        <el-option label="特殊占用" value="特殊占用"></el-option>
        <el-option label="异常处理" value="异常处理"></el-option>
      </el-select>
      
      <el-select v-model="filterVersion" placeholder="版本" clearable style="width: 100px; margin-right: 10px;" @change="handleSearch">
        <el-option label="WiFi" value="WiFi"></el-option>
        <el-option label="4G" value="4G"></el-option>
      </el-select>
      <el-select v-model="filterType" placeholder="类型" clearable style="width: 100px; margin-right: 10px;" @change="handleSearch">
        <el-option label="睡眠" value="睡眠"></el-option>
        <el-option label="跌倒" value="跌倒"></el-option>
      </el-select>
      <el-select v-model="filterPackaging" placeholder="包装" clearable style="width: 100px; margin-right: 10px;" @change="handleSearch">
        <el-option label="简约" value="简约"></el-option>
        <el-option label="精品" value="精品"></el-option>
      </el-select>

      <el-select v-model="filterIoTCard" placeholder="IoT卡(4G)" clearable style="width: 110px; margin-right: 10px;" @change="onIoTCardFilterChange">
        <el-option label="已开卡" value="开卡"></el-option>
        <el-option label="已关卡" value="关卡"></el-option>
      </el-select>
      
      <el-select v-model="filterOwner" placeholder="归属人" clearable style="width: 150px; margin-right: 10px;" @change="handleSearch">
        <el-option v-for="owner in ownerOptions" :key="owner" :label="owner" :value="owner"></el-option>
      </el-select>

      <el-date-picker
        v-model="filterDeliveryDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="交付开始日期"
        end-placeholder="交付结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        style="width: 280px; margin-right: 10px;"
        clearable
        @change="handleSearch"
      />

      <el-button type="primary" @click="showAddDialog = true">新增设备</el-button>
      <el-button type="primary" @click="showBatchAddDialog = true">批量录入</el-button>
      <el-button type="success" @click="showImportDialog = true">
        <el-icon><Upload /></el-icon> 批量导入
      </el-button>
      <el-button type="warning" @click="exportInventory">
        <el-icon><Download /></el-icon> 导出
      </el-button>
      <el-button @click="clearFilters" style="margin-left: 10px;">清除筛选</el-button>
      <el-button v-if="selectedIds.length > 0" type="primary" @click="openBatchEdit" style="margin-left: 10px;">
        批量编辑 ({{ selectedIds.length }})
      </el-button>
      <el-button v-if="selectedIds.length > 0" type="danger" @click="batchDelete" style="margin-left: 10px;">
        批量删除 ({{ selectedIds.length }})
      </el-button>
    </div>

    <el-table
      :data="inventoryList"
      v-loading="loading"
      style="width: 100%"
      border
      stripe
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="device_id" label="设备号" width="150" sortable></el-table-column>
      <el-table-column prop="version" label="版本" width="80" sortable></el-table-column>
      <el-table-column prop="type" label="类型" width="80"></el-table-column>
      <el-table-column prop="packaging" label="包装" width="80"></el-table-column>
      <el-table-column prop="device_attribute" label="设备属性" width="130" sortable>
        <template #default="{ row }">
          <el-tag :type="getAttributeType(row.device_attribute)" size="small">
            {{ row.device_attribute }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="owner" label="归属人" width="120" sortable></el-table-column>
      <el-table-column prop="borrower" label="领用人" width="100"></el-table-column>
      <el-table-column prop="sales_person" label="销售" width="100"></el-table-column>
      <el-table-column prop="iot_card_status" label="IoT卡" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.iot_card_status === '开卡'" type="success" size="small">开卡</el-tag>
          <el-tag v-else-if="row.iot_card_status === '关卡'" type="danger" size="small">关卡</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="remarks" label="备注" min-width="150" show-overflow-tooltip></el-table-column>
      <el-table-column prop="delivery_date" label="交付时间" width="120" sortable>
        <template #default="{ row }">
          {{ row.delivery_date ? new Date(row.delivery_date).toLocaleDateString() : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="showDetail(row)">详情</el-button>
          <el-button size="small" @click="editItem(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteItem(row.device_id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
      :current-page="currentPage"
      :page-sizes="[10, 20, 50, 100]"
      :page-size="pageSize"
      layout="total, sizes, prev, pager, next, jumper"
      :total="totalItems">
    </el-pagination>

    <!-- 编辑/新增对话框 -->
    <el-dialog
      :title="editingItem ? '编辑设备' : '新增设备'"
      v-model="showAddDialog"
      width="60%"
      :before-close="handleClose"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="设备号" prop="device_id">
          <el-input v-model="form.device_id" :disabled="!!editingItem"></el-input>
        </el-form-item>
        <el-form-item label="版本" prop="version">
          <el-select v-model="form.version" placeholder="请选择版本" @change="onVersionChange">
            <el-option label="WiFi" value="WiFi"></el-option>
            <el-option label="4G" value="4G"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择类型">
            <el-option label="睡眠" value="睡眠"></el-option>
            <el-option label="跌倒" value="跌倒"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="包装" prop="packaging">
          <el-select v-model="form.packaging" placeholder="请选择包装">
            <el-option label="简约" value="简约"></el-option>
            <el-option label="精品" value="精品"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="设备属性" prop="device_attribute">
          <el-select v-model="form.device_attribute" placeholder="请选择设备属性">
            <el-option label="产品演示" value="产品演示"></el-option>
            <el-option label="技术开发/测试" value="技术开发/测试"></el-option>
            <el-option label="内部试用" value="内部试用"></el-option>
            <el-option label="商机试用" value="商机试用"></el-option>
            <el-option label="特殊占用" value="特殊占用"></el-option>
            <el-option label="现有库存" value="现有库存"></el-option>
            <el-option label="异常处理" value="异常处理"></el-option>
            <el-option label="商机交付" value="商机交付"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="归属人" prop="owner">
          <el-input v-model="form.owner"></el-input>
        </el-form-item>
        <el-form-item label="领用人" prop="borrower">
          <el-input v-model="form.borrower"></el-input>
        </el-form-item>
        <el-form-item label="销售" prop="sales_person">
          <el-input v-model="form.sales_person"></el-input>
        </el-form-item>
        <el-form-item label="IoT卡状态" prop="iot_card_status" v-if="form.version === '4G'">
          <el-select v-model="form.iot_card_status" placeholder="请选择IoT卡状态" clearable>
            <el-option label="开卡" value="开卡"></el-option>
            <el-option label="关卡" value="关卡"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="备注" prop="remarks">
          <el-input v-model="form.remarks" type="textarea"></el-input>
        </el-form-item>
        <el-form-item label="补充信息" prop="supplementary_info">
          <el-input v-model="form.supplementary_info" type="textarea"></el-input>
        </el-form-item>
        <el-form-item label="交付时间" prop="delivery_date">
          <el-date-picker
            v-model="form.delivery_date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD">
          </el-date-picker>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 批量录入对话框 -->
    <el-dialog title="批量录入设备" v-model="showBatchAddDialog" width="900px">
      <el-alert title="直接在表格中输入设备信息，一行一台。设备号必填。" type="info" :closable="false" style="margin-bottom: 12px;" />
      <el-table :data="batchFormRows" border stripe style="width: 100%">
        <el-table-column label="设备号" width="160">
          <template #default="{ row }"><el-input v-model="row.device_id" placeholder="必填" size="small" /></template>
        </el-table-column>
        <el-table-column label="版本" width="90">
          <template #default="{ row }">
            <el-select v-model="row.version" size="small"><el-option label="WiFi" value="WiFi" /><el-option label="4G" value="4G" /></el-select>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-select v-model="row.type" size="small"><el-option label="睡眠" value="睡眠" /><el-option label="跌倒" value="跌倒" /></el-select>
          </template>
        </el-table-column>
        <el-table-column label="属性" width="130">
          <template #default="{ row }">
            <el-select v-model="row.device_attribute" size="small">
              <el-option label="现有库存" value="现有库存" /><el-option label="商机交付" value="商机交付" />
              <el-option label="商机试用" value="商机试用" /><el-option label="产品演示" value="产品演示" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="归属人" width="120">
          <template #default="{ row }"><el-input v-model="row.owner" placeholder="可选" size="small" /></template>
        </el-table-column>
        <el-table-column label="备注" min-width="150">
          <template #default="{ row }"><el-input v-model="row.remarks" placeholder="可选" size="small" /></template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ $index }">
            <el-button size="small" type="danger" @click="batchFormRows.splice($index, 1)" :disabled="batchFormRows.length <= 1">×</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 12px; display: flex; gap: 8px;">
        <el-button size="small" @click="batchFormRows.push({device_id:'',version:'WiFi',type:'睡眠',packaging:'简约',device_attribute:'现有库存',owner:'',remarks:''})">+ 添加一行</el-button>
        <span style="color: #909399; font-size: 12px; line-height: 32px; margin-left: 8px;">共 {{ batchFormRows.length }} 行</span>
      </div>
      <template #footer>
        <el-button @click="showBatchAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitBatchAdd" :loading="batchAdding">批量创建 ({{ batchFormRows.filter(r=>r.device_id.trim()).length }} 台)</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog
      title="批量导入设备"
      v-model="showImportDialog"
      width="600px"
    >
      <el-alert
        title="导入说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;">
        <p>1. 请下载导入模板，按照模板格式填写数据</p>
        <p>2. 支持CSV文件格式</p>
        <p>3. 必填字段：设备号。版本可选(WiFi/4G)，类型可选(睡眠/跌倒)，包装可选(简约/精品)</p>
        <p>4. 如果设备号已存在，将覆盖更新该设备信息</p>
      </el-alert>
      
      <div style="text-align: center; margin-bottom: 20px;">
        <el-button type="primary" @click="downloadTemplate">
          <el-icon><Download /></el-icon> 下载导入模板
        </el-button>
      </div>

      <el-upload
        ref="uploadRef"
        class="upload-demo"
        drag
        action="#"
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".csv"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            只能上传CSV文件
          </div>
        </template>
      </el-upload>

      <div v-if="importResult" style="margin-top: 20px;">
        <el-alert
          :title="importResult.message"
          :type="importResult.error_count > 0 ? 'warning' : 'success'"
          :closable="false"
        >
          <p>成功导入：{{ importResult.success_count }} 条</p>
          <p v-if="importResult.error_count > 0">失败：{{ importResult.error_count }} 条</p>
        </el-alert>
        
        <div v-if="importResult.errors && importResult.errors.length > 0" style="margin-top: 10px; max-height: 200px; overflow-y: auto;">
          <h4>错误详情：</h4>
          <ul>
            <li v-for="(error, index) in importResult.errors" :key="index" style="color: #f56c6c; font-size: 12px;">
              {{ error }}
            </li>
          </ul>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeImportDialog">关闭</el-button>
          <el-button type="primary" @click="submitImport" :loading="importing">
            开始导入
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 批量编辑对话框 -->
    <el-dialog
      title="批量编辑设备"
      v-model="showBatchEditDialog"
      width="600px"
    >
      <el-alert
        title="正在编辑 {{ selectedIds.length }} 台设备"
        type="info"
        :closable="false"
        style="margin-bottom: 16px;"
      >
        只填写需要批量修改的字段，留空的字段不会被修改。如需清空某个字段，请输入一个空格后回车。
      </el-alert>
      <el-form :model="batchEditForm" label-width="100px">
        <el-form-item label="设备属性">
          <el-select v-model="batchEditForm.device_attribute" placeholder="不修改" clearable>
            <el-option label="产品演示" value="产品演示"></el-option>
            <el-option label="技术开发/测试" value="技术开发/测试"></el-option>
            <el-option label="内部试用" value="内部试用"></el-option>
            <el-option label="商机试用" value="商机试用"></el-option>
            <el-option label="特殊占用" value="特殊占用"></el-option>
            <el-option label="现有库存" value="现有库存"></el-option>
            <el-option label="异常处理" value="异常处理"></el-option>
            <el-option label="商机交付" value="商机交付"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="归属人">
          <el-input v-model="batchEditForm.owner" placeholder="不修改" clearable></el-input>
        </el-form-item>
        <el-form-item label="领用人">
          <el-input v-model="batchEditForm.borrower" placeholder="不修改" clearable></el-input>
        </el-form-item>
        <el-form-item label="销售">
          <el-input v-model="batchEditForm.sales_person" placeholder="不修改" clearable></el-input>
        </el-form-item>
        <el-form-item label="IoT卡状态" v-if="!batchHasWifiDevice">
          <el-select v-model="batchEditForm.iot_card_status" placeholder="不修改" clearable>
            <el-option label="开卡" value="开卡"></el-option>
            <el-option label="关卡" value="关卡"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="batchEditForm.remarks" type="textarea" placeholder="不修改"></el-input>
        </el-form-item>
        <el-form-item label="补充信息">
          <el-input v-model="batchEditForm.supplementary_info" type="textarea" placeholder="不修改"></el-input>
        </el-form-item>
        <el-form-item label="交付时间">
          <el-date-picker
            v-model="batchEditForm.delivery_date"
            type="date"
            placeholder="不修改"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            clearable>
          </el-date-picker>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatchEditDialog = false">取消</el-button>
        <el-button type="primary" @click="submitBatchEdit" :loading="batchEditing">
          确认批量更新
        </el-button>
      </template>
    </el-dialog>

    <!-- 设备详情对话框 -->
    <el-dialog title="设备详情" v-model="showDetailDialog" width="700px">
      <div v-if="detailData" style="max-height: 500px; overflow-y: auto;">
        <el-descriptions :column="2" border style="margin-bottom: 20px;">
          <el-descriptions-item label="设备号" span="2">{{ detailData.device.device_id }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ detailData.device.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ detailData.device.type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="包装">{{ detailData.device.packaging || '-' }}</el-descriptions-item>
          <el-descriptions-item label="设备属性">{{ detailData.device.device_attribute || '-' }}</el-descriptions-item>
          <el-descriptions-item label="归属人">{{ detailData.device.owner || '-' }}</el-descriptions-item>
          <el-descriptions-item label="领用人">{{ detailData.device.borrower || '-' }}</el-descriptions-item>
          <el-descriptions-item label="销售">{{ detailData.device.sales_person || '-' }}</el-descriptions-item>
          <el-descriptions-item label="交付时间">{{ detailData.device.delivery_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" span="2">{{ detailData.device.remarks || '-' }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin-bottom: 10px;">借用历史 ({{ detailData.borrow_history.length }}条)</h4>
        <el-table :data="detailData.borrow_history" border size="small" v-if="detailData.borrow_history.length > 0">
          <el-table-column prop="borrower" label="借用人" width="100"></el-table-column>
          <el-table-column prop="borrow_date" label="借用时间" width="150"></el-table-column>
          <el-table-column prop="expected_return_date" label="应还日期" width="100"></el-table-column>
          <el-table-column prop="actual_return_date" label="实际归还" width="100"></el-table-column>
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'returned' ? 'success' : row.status === 'overdue' ? 'danger' : 'warning'" size="small">
                {{ row.status === 'returned' ? '已归还' : row.status === 'overdue' ? '逾期' : '借出中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="purpose" label="目的" min-width="120"></el-table-column>
        </el-table>
        <el-empty v-else description="无借用记录" />
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, reactive } from 'vue';
import { inventoryAPI } from '../api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search, Upload, Download, UploadFilled } from '@element-plus/icons-vue';

export default {
  name: 'Inventory',
  components: { Search, Upload, Download, UploadFilled },
  setup() {
    const inventoryList = ref([]);
    const loading = ref(false);
    const currentPage = ref(1);
    const pageSize = ref(10);
    const totalItems = ref(0);
    const showAddDialog = ref(false);
    const showDetailDialog = ref(false);
    const detailData = ref(null);
    const editingItem = ref(null);
    
    // 批量录入
    const showBatchAddDialog = ref(false);
    const batchAdding = ref(false);
    const showBatchEditDialog = ref(false);
    const batchEditing = ref(false);
    const batchHasWifiDevice = ref(false);
    const batchEditForm = reactive({
      device_attribute: '',
      owner: '',
      borrower: '',
      sales_person: '',
      iot_card_status: '',
      remarks: '',
      supplementary_info: '',
      delivery_date: null
    });
    const batchFormRows = ref([
      { device_id: '', version: 'WiFi', type: '睡眠', packaging: '简约', device_attribute: '现有库存', owner: '', remarks: '' }
    ]);

    const submitBatchAdd = async () => {
      const validRows = batchFormRows.value.filter(r => r.device_id.trim());
      if (validRows.length === 0) { ElMessage.warning('请至少填写一台设备号'); return; }
      batchAdding.value = true;
      let ok = 0, fail = 0;
      for (const row of validRows) {
        try {
          await inventoryAPI.create({ ...row, serial_number: row.device_id });
          ok++;
        } catch (e) { fail++; }
      }
      batchAdding.value = false;
      ElMessage.success(`批量录入完成: 成功 ${ok} 台` + (fail > 0 ? `, 失败 ${fail} 台` : ''));
      if (ok > 0) loadInventory();
      showBatchAddDialog.value = false;
    };

    // 导入导出相关
    const showImportDialog = ref(false);
    const importFile = ref(null);
    const importing = ref(false);
    const importResult = ref(null);
    const uploadRef = ref(null);
    
    // 搜索和筛选
    const searchText = ref('');
    const filterAttribute = ref('');
    const filterVersion = ref('');
    const filterType = ref('');
    const filterPackaging = ref('');
    const filterOwner = ref(''); // 归属人筛选
    const ownerOptions = ref([]); // 动态归属人列表
    const filterDeliveryDateRange = ref(null); // 交付时间范围筛选
    const filterIoTCard = ref('');
    
    // 获取属性标签类型
    const getAttributeType = (attribute) => {
      const typeMap = {
        '现有库存': '',
        '商机交付': 'success',
        '商机试用': 'warning',
        '内部试用': 'info',
        '产品演示': '',
        '技术开发/测试': 'info',
        '特殊占用': 'warning',
        '异常处理': 'danger'
      };
      return typeMap[attribute] || '';
    };
    
    // 搜索处理 - 调用后端API
    const handleSearch = () => {
      // 搜索时重置到第一页
      currentPage.value = 1;
      loadInventory();
    };
    
    // 清除所有筛选
    const clearFilters = () => {
      searchText.value = '';
      filterAttribute.value = '';
      filterVersion.value = '';
      filterType.value = '';
      filterPackaging.value = '';
      filterOwner.value = '';
      filterDeliveryDateRange.value = null;
      filterIoTCard.value = '';
      currentPage.value = 1;
      loadInventory();
    };

    // 重置表单到默认值
    const resetForm = () => {
      form.serial_number = '';
      form.version = 'WiFi';
      form.device_id = '';
      form.type = '睡眠';
      form.packaging = '简约';
      form.device_attribute = '现有库存';
      form.owner = '';
      form.borrower = '';
      form.sales_person = '';
      form.iot_card_status = '';
      form.remarks = '';
      form.supplementary_info = '';
      form.delivery_date = null;
      editingItem.value = null;
    };

    // 版本切换时清除IoT卡状态（WiFi设备不需要IoT卡）
    const onVersionChange = (val) => {
      if (val === 'WiFi') {
        form.iot_card_status = '';
      }
    };

    // IoT卡筛选时自动切换到4G版本（因为只有4G设备有IoT卡）
    const onIoTCardFilterChange = (val) => {
      if (val && filterVersion.value !== '4G') {
        filterVersion.value = '4G';
      }
      handleSearch();
    };

    const form = reactive({
      serial_number: '',
      version: 'WiFi',
      device_id: '',
      type: '睡眠',
      packaging: '简约',
      device_attribute: '现有库存',
      owner: '',
      borrower: '',
      sales_person: '',
      iot_card_status: '',
      remarks: '',
      supplementary_info: '',
      delivery_date: null
    });

    const rules = {
      device_id: [
        { required: true, message: '请输入设备号', trigger: 'blur' },
        { min: 12, max: 12, message: '设备号必须为12位（3字母+9数字）', trigger: 'blur' },
        { pattern: /^[A-Za-z]{3}\d{9}$/, message: '格式: 3位字母+9位数字, 如CAA241101356', trigger: 'blur' }
      ]
    };
    
    const formRef = ref(null);

    const loadOwners = async () => {
      try {
        const owners = await inventoryAPI.getOwners();
        ownerOptions.value = owners || [];
      } catch (e) {
        console.error('加载归属人列表失败:', e);
      }
    };

    const loadInventory = async () => {
      loading.value = true;
      try {
        const params = {
          skip: (currentPage.value - 1) * pageSize.value,
          limit: pageSize.value,
          search: searchText.value,
          device_attribute: filterAttribute.value,
          version: filterVersion.value,
          type: filterType.value,
          packaging: filterPackaging.value,
          owner: filterOwner.value,
          iot_card_status: filterIoTCard.value
        };
        
        // 添加交付时间范围参数
        if (filterDeliveryDateRange.value && filterDeliveryDateRange.value.length === 2) {
          params.delivery_date_start = filterDeliveryDateRange.value[0];
          params.delivery_date_end = filterDeliveryDateRange.value[1];
        }
        
        const response = await inventoryAPI.getAll(params);
        // 后端现在返回 { total: xxx, items: [...] }
        inventoryList.value = response.items || response;
        totalItems.value = response.total || 0;
      } catch (error) {
        console.error('加载设备列表失败:', error);
        ElMessage.error('加载设备列表失败');
      } finally {
        loading.value = false;
      }
    };

    const editItem = (item) => {
      editingItem.value = item;
      Object.assign(form, item);
      showAddDialog.value = true;
    };

    // 查看设备详情
    const showDetail = async (item) => {
      try {
        const resp = await inventoryAPI.getDetail(item.device_id);
        detailData.value = resp;
        showDetailDialog.value = true;
      } catch (error) {
        console.error('加载设备详情失败:', error);
        ElMessage.error('加载设备详情失败');
      }
    };

    const deleteItem = async (deviceId) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除设备 ${deviceId} 吗？`,
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );
        
        await inventoryAPI.delete(deviceId);
        ElMessage.success('设备删除成功');
        loadInventory(); // 重新加载列表
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除设备失败:', error);
          ElMessage.error('删除设备失败');
        }
      }
    };

    const submitForm = async () => {
      const valid = await formRef.value.validate().catch(() => false);
      if (!valid) return;
      try {
        if (editingItem.value) {
          // 更新设备
          await inventoryAPI.update(editingItem.value.device_id, form);
          ElMessage.success('设备信息更新成功');
        } else {
          // 创建新设备
          await inventoryAPI.create(form);
          ElMessage.success('设备创建成功');
        }
        
        showAddDialog.value = false;
        resetForm();
        loadInventory(); // 重新加载列表
      } catch (error) {
        console.error('提交表单失败:', error);
        const detail = error.response?.data?.detail;
        ElMessage.error(detail || '操作失败');
      }
    };

    const handleClose = (done) => {
      resetForm();
      done();
    };

    const handleSizeChange = (val) => {
      pageSize.value = val;
      loadInventory();
    };

    const handleCurrentChange = (val) => {
      currentPage.value = val;
      loadInventory();
    };

    // 下载导入模板（使用 axios blob 避免 token 泄露到 URL）
    const downloadTemplate = async () => {
      try {
        const response = await inventoryAPI.downloadTemplate();
        const blob = new Blob([response], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'inventory_import_template.csv';
        a.click(); URL.revokeObjectURL(url);
      } catch { ElMessage.error('下载模板失败'); }
    };

    // 多选
    const selectedIds = ref([]);
    const handleSelectionChange = (rows) => { selectedIds.value = rows.map(r => r.device_id); };

    // 批量编辑
    const openBatchEdit = () => {
      // 重置表单
      Object.keys(batchEditForm).forEach(k => {
        batchEditForm[k] = k === 'delivery_date' ? null : '';
      });
      // 检查选中设备中是否有WiFi设备，WiFi设备无IoT卡不应显示IoT卡编辑
      const selectedSet = new Set(selectedIds.value);
      batchHasWifiDevice.value = inventoryList.value.some(
        d => selectedSet.has(d.device_id) && d.version === 'WiFi'
      );
      showBatchEditDialog.value = true;
    };

    const submitBatchEdit = async () => {
      // 构建只包含非空字段的更新数据
      const updateData = {};
      for (const [key, value] of Object.entries(batchEditForm)) {
        if (value !== null && value !== '' && value !== undefined) {
          updateData[key] = value;
        }
      }
      if (Object.keys(updateData).length === 0) {
        ElMessage.warning('请至少填写一个要修改的字段');
        return;
      }
      batchEditing.value = true;
      try {
        const res = await inventoryAPI.batchUpdate(selectedIds.value, updateData);
        ElMessage.success(res.message || `成功更新 ${res.updated} 台设备`);
        showBatchEditDialog.value = false;
        selectedIds.value = [];
        loadInventory();
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || '批量编辑失败');
      } finally {
        batchEditing.value = false;
      }
    };

    // 批量删除
    const batchDelete = async () => {
      try {
        await ElMessageBox.confirm(`确认删除 ${selectedIds.value.length} 台设备？不可恢复！`, '批量删除', { type: 'warning' });
        const res = await inventoryAPI.batchDelete(selectedIds.value);
        ElMessage.success(res.message || `已删除 ${res.deleted} 台`);
        selectedIds.value = [];
        loadInventory();
      } catch (e) {
        if (e !== 'cancel') ElMessage.error('批量删除失败');
      }
    };

    // 导出库存数据（带入当前筛选条件，使用 blob 避免 token 泄露）
    const exportInventory = async () => {
      try {
        const params = {};
        if (searchText.value) params.search = searchText.value;
        if (filterAttribute.value) params.device_attribute = filterAttribute.value;
        if (filterVersion.value) params.version = filterVersion.value;
        if (filterType.value) params.type = filterType.value;
        if (filterPackaging.value) params.packaging = filterPackaging.value;
        if (filterOwner.value) params.owner = filterOwner.value;
        if (filterIoTCard.value) params.iot_card_status = filterIoTCard.value;
        if (filterDeliveryDateRange.value && filterDeliveryDateRange.value.length === 2) {
          params.delivery_date_start = filterDeliveryDateRange.value[0];
          params.delivery_date_end = filterDeliveryDateRange.value[1];
        }
        const response = await inventoryAPI.exportCSV(params);
        const blob = new Blob([response], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const now = new Date();
        a.href = url;
        a.download = `inventory_${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}${String(now.getSeconds()).padStart(2,'0')}.csv`;
        a.click(); URL.revokeObjectURL(url);
        ElMessage.success('导出完成');
      } catch { ElMessage.error('导出失败'); }
    };

    // 处理文件选择
    const handleFileChange = (file) => {
      importFile.value = file.raw;
      importResult.value = null;
    };

    // 提交导入
    const submitImport = async () => {
      if (!importFile.value) {
        ElMessage.warning('请先选择要导入的文件');
        return;
      }

      importing.value = true;
      try {
        const formData = new FormData();
        formData.append('file', importFile.value);

        const response = await inventoryAPI.importCSV(formData);
        importResult.value = response;
        
        if (response.success_count > 0) {
          ElMessage.success(`导入成功 ${response.success_count} 条记录`);
          loadInventory(); // 重新加载列表
        }

        if (response.error_count > 0) {
          ElMessage.warning(`有 ${response.error_count} 条记录导入失败，请查看错误详情`);
        }
      } catch (error) {
        console.error('导入失败:', error);
        ElMessage.error(error.response?.data?.detail || '导入失败');
      } finally {
        importing.value = false;
      }
    };

    // 关闭导入对话框
    const closeImportDialog = () => {
      showImportDialog.value = false;
      importFile.value = null;
      importResult.value = null;
      if (uploadRef.value) {
        uploadRef.value.clearFiles();
      }
    };

    onMounted(() => {
      loadInventory();
      loadOwners();
      window.addEventListener('ai-data-changed', loadInventory);
    });

    onUnmounted(() => {
      window.removeEventListener('ai-data-changed', loadInventory);
    });

    return {
      inventoryList,
      loading,
      currentPage,
      pageSize,
      totalItems,
      showAddDialog,
      showDetailDialog,
      detailData,
      showImportDialog,
      editingItem,
      form,
      rules,
      formRef,
      searchText,
      filterAttribute,
      filterVersion,
      filterType,
      filterPackaging,
      filterOwner,
      ownerOptions,
      filterDeliveryDateRange,
      importFile,
      importing,
      importResult,
      uploadRef,
      getAttributeType,
      handleSearch,
      clearFilters,
      onVersionChange,
      onIoTCardFilterChange,
      editItem,
      deleteItem,
      showDetail,
      submitForm,
      handleClose,
      handleSizeChange,
      handleCurrentChange,
      downloadTemplate,
      selectedIds, handleSelectionChange, batchDelete,
      showBatchAddDialog, batchAdding, batchFormRows, submitBatchAdd,
      showBatchEditDialog, batchEditing, batchHasWifiDevice, batchEditForm,
      openBatchEdit, submitBatchEdit,
      exportInventory,
      handleFileChange,
      submitImport,
      closeImportDialog
    };
  }
};
</script>

<style scoped>
.inventory {
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.dialog-footer {
  text-align: right;
}
</style>