# 安装（首次运行）
# if (!require("BiocManager", quietly = TRUE))
#   install.packages("BiocManager")
# BiocManager::install(c("TCGAbiolinks","limma","clusterProfiler","org.Hs.eg.db","GEOquery","survival","glmnet","dplyr","tidyr","ggplot2"))

# 加载包
library(TCGAbiolinks)
library(limma)
library(clusterProfiler)
library(org.Hs.eg.db)
library(GEOquery)
library(survival)
library(glmnet)
library(dplyr)
library(ggplot2)
set.seed(123)  # 固定随机数，结果可重复
#第一步：TCGA-LIHC 肝癌 vs 正常 limma 差异分析（发现集）
#1.1 下载 & 整理数据
# 下载TCGA-LIHC RNA-seq计数数据
query <- GDCquery(
  project = "TCGA-LIHC",
  data.category = "Transcriptome Profiling",
  data.type = "Gene Expression Quantification",
  workflow.type = "STAR - Counts"
)
 GDCdownload(query, files.per.chunk = 10)#,method = "client")

data <- GDCprepare(query)
save(data,file = "data.RData")
# 表达矩阵+样本信息
library(SummarizedExperiment)
count_mat <- assay(data)
sample_info <- colData(data) %>% as.data.frame()

# 筛选：癌组织Primary Tumor / 癌旁正常Solid Tissue Normal
keep_sample <- sample_info$sample_type %in% c("Primary Tumor","Solid Tissue Normal")
count_mat <- count_mat[,keep_sample]
group <- factor(ifelse(sample_info$sample_type[keep_sample]=="Primary Tumor","Tumor","Normal"),
                levels = c("Normal","Tumor"))
#1.2 limma 差异分析
# CPM标准化+log2转换
cpm_mat <- edgeR::cpm(count_mat)
log2cpm <- log2(cpm_mat + 1)

# 过滤低表达基因
keep_gene <- rowSums(log2cpm > 1) >= 10
log2cpm_filter <- log2cpm[keep_gene,]

# 构建设计矩阵+对比
design <- model.matrix(~0 + group)
colnames(design) <- levels(group)
contrast <- makeContrasts(Tumor - Normal, levels = design)

# limma建模
fit <- lmFit(log2cpm_filter, design)
fit2 <- contrasts.fit(fit, contrast)
fit2 <- eBayes(fit2)

# 提取全部差异结果
tcga_deg_all <- topTable(fit2, coef = 1, adjust = "fdr", number = Inf)

# 筛选差异基因：adj.P<0.05 & |log2FC|≥1
tcga_deg <- tcga_deg_all %>%
  filter(adj.P.Val < 0.05, abs(logFC) >= 1)

# 保存TCGA差异基因
write.csv(tcga_deg,"1.TCGA_LIHC_DEG.csv",row.names = T)
# 第二步：外部验证队列 1 —— GSE14520 差异验证
# 下载GSE14520
library(data.table)
gse=tinyarray::geo_download("GSE14520")

gse <-getGEO("GSE76427")
gse_exp <- gse$exp
gse_phe <- gse$pd

# 自行分组（HCC vs 正常肝组织，根据GSE14520注释调整）
# 这里简化分组逻辑，你可根据平台注释微调
unique(gse_phe$characteristics_ch1)
group_gse <- ifelse(grepl("non[- ]tumor", gse_phe$characteristics_ch1, ignore.case = TRUE),
                    "Normal",
                    ifelse(grepl("tumor", gse_phe$characteristics_ch1, ignore.case = TRUE),
                           "Tumor", NA))

group_gse <- factor(group_gse)

# limma差异
design_gse <- model.matrix(~0 + group_gse)
colnames(design_gse) <- levels(group_gse)
contrast_gse <- makeContrasts(Tumor-Normal,levels = design_gse)

fit_gse <- lmFit(gse_exp, design_gse)
fit_gse2 <- contrasts.fit(fit_gse, contrast_gse)
fit_gse2 <- eBayes(fit_gse2)

gse_deg_all <- topTable(fit_gse2,coef = 1,adjust = "fdr",number = Inf)
gse_deg <- gse_deg_all %>% filter(adj.P.Val < 0.05, abs(logFC)>=1)

write.csv(gse_deg,"2.GSE14520_DEG.csv",row.names = T)
#第三步：外部验证队列 2 —— ICGC-LIRI-JP 差异验证
# ICGC 采用 FPKM/TPM 表达矩阵，同样 limma 做癌 vs 正常差异，保留两个数据库与 TCGA 表达趋势一致基因
# 1. 自行导入ICGC-LIRI-JP表达矩阵+临床分组（ICGC官网下载）
# icgc_exp：行=基因，列=样本
# icgc_group：Tumor / Normal

# 2. 统一limma分析流程（和TCGA、GSE完全一致）
design_icgc <- model.matrix(~0 + icgc_group)
contrast_icgc <- makeContrasts(Tumor-Normal,levels = design_icgc)

fit_icgc <- lmFit(icgc_exp, design_icgc)
fit_icgc2 <- contrasts.fit(fit_icgc, contrast_icgc)
fit_icgc2 <- eBayes(fit_icgc2)

icgc_deg_all <- topTable(fit_icgc2,coef = 1,adjust = "fdr",number = Inf)
icgc_deg <- icgc_deg_all %>% filter(adj.P.Val < 0.05, abs(logFC)>=1)

write.csv(icgc_deg,"3.ICGC_LIRI_JP_DEG.csv",row.names = T)

# 关键：三队列交集差异基因（TCGA+GSE14520+ICGC共同差异、趋势一致）
common_deg <- intersect(intersect(rownames(tcga_deg),rownames(gse_deg)),rownames(icgc_deg))
#第四步：获取权威内质网（ER）基因集 & 基因交集
# 4.1 内质网标准基因集（论文可用）
# GO:0005783 ：内质网细胞组分
# KEGG hsa04131：内质网蛋白加工
# 内质网GO基因集
er_go <- getGOgenes(GOid = "GO:0005783", OrgDb = org.Hs.eg.db, keyType = "SYMBOL")
# 内质网应激+UPR
ers_go <- getGOgenes(GOid = "GO:0034976", OrgDb = org.Hs.eg.db, keyType = "SYMBOL")

# 合并全部内质网相关基因
er_all_gene <- unique(c(er_go,ers_go))

# 4.2 多队列共同差异基因 ∩ 内质网基因
# 前提：将Ensembl ID转为GeneSymbol（前面已写转换代码）
common_deg_symbol <- 你的基因名向量
er_intersect_gene <- intersect(common_deg_symbol, er_all_gene)

# 得到：内质网相关差异基因 ER-DEGs
writeLines(er_intersect_gene,"4.ER_related_DEGs.txt")
#第五步：单因素 Cox 回归分析（ER-DEGs 预后初筛）
# 提取TCGA肿瘤样本临床生存数据
cli <- colData(data) %>% as.data.frame()
cli_tumor <- cli[cli$sample_type=="Primary Tumor",]

# 生存时间+生存状态
cli_tumor$os_time <- ifelse(is.na(cli_tumor$days_to_death),
                            cli_tumor$days_to_last_follow_up,
                            cli_tumor$days_to_death)
cli_tumor$os_time <- as.numeric(cli_tumor$os_time)
cli_tumor$status <- ifelse(cli_tumor$vital_status=="Dead",1,0)

# 单因素Cox循环
univ_cox_res <- data.frame()
for(g in er_intersect_gene){
  # 提取单个基因表达
  exp_g <- log2cpm_filter[基因对应行名,rownames(cli_tumor)]
  surv_obj <- Surv(time = cli_tumor$os_time, event = cli_tumor$status)
  cox_fit <- coxph(surv_obj ~ exp_g)
  cox_s <- summary(cox_fit)
  
  res_line <- data.frame(
    Gene = g,
    HR = cox_s$coefficients[,2],
    Pvalue = cox_s$coefficients[,5]
  )
  univ_cox_res <- rbind(univ_cox_res,res_line)
}

# 筛选单因素Cox显著基因 P<0.05
cox_sig_gene <- univ_cox_res %>% filter(Pvalue < 0.05) %>% pull(Gene)
write.csv(univ_cox_res,"5.单因素Cox结果.csv",row.names = F)
#第六步：LASSO-Cox + 10 折交叉验证 筛选最终候选基因
# 构建表达矩阵+生存数据
expr_lasso <- t(log2cpm_filter[匹配cox_sig_gene行名, rownames(cli_tumor)])
surv_time <- cli_tumor$os_time
surv_event <- cli_tumor$status

# 生存响应变量
y <- Surv(surv_time, surv_event)

# 10折交叉验证找最优lambda
cvfit <- cv.glmnet(expr_lasso, y, 
                   family = "cox", 
                   nfolds = 10)

# 最优λ.min
best_lambda <- cvfit$lambda.min

# 拟合LASSO模型
lasso_fit <- glmnet(expr_lasso, y, 
                    family = "cox", 
                    lambda = best_lambda)

# 提取非零系数基因 = 最终候选预后基因
coef_mat <- coef(lasso_fit)
final_gene <- names(which(coef_mat[,1] != 0))

# 保存最终建模基因
writeLines(final_gene,"6.LASSO最终候选基因.txt")


# R 代码画出你图里的火山图 + 韦恩交集图，完全对应你的 HCC 差异基因 + 内质网基因交集场景。一、火山图（Volcano Plot）
# 核心逻辑
# 用差异分析结果里的 logFC 和 adj.P.Val 画点，按阈值（adj.P<0.05 & |log2FC|≥1）给点上色。
# 完整代码（直接运行）# 加载包
library(ggplot2)

# 用你前面的TCGA差异结果 tcga_deg_all
# 先给结果加分组标签
tcga_deg_all$sig <- case_when(
  tcga_deg_all$adj.P.Val < 0.05 & tcga_deg_all$logFC >= 1 ~ "Upregulated",
  tcga_deg_all$adj.P.Val < 0.05 & tcga_deg_all$logFC <= -1 ~ "Downregulated",
  TRUE ~ "Not Significant"
)

# 画火山图
ggplot(tcga_deg_all, aes(x = logFC, y = -log10(adj.P.Val))) +
  geom_point(aes(color = sig), alpha = 0.7, size = 1) +
  scale_color_manual(values = c("blue", "gray", "red")) +
  # 阈值线
  geom_vline(xintercept = c(-1, 1), linetype = "dashed", color = "black") +
  geom_hline(yintercept = -log10(0.05), linetype = "dashed", color = "black") +
  # 标签
  labs(
    x = "log2(Fold Change)",
    y = "-log10(Adjusted p-value)",
    color = "Significance",
    title = "Differential Expression Genes (TCGA-LIHC)"
  ) +
  theme_minimal() +
  theme(plot.title = element_text(hjust = 0.5))
