# 
# 
# 
# 
# 
# library(TCGAbiolinks)
# library(dplyr)
# library(readr)
# 
# # 获取所有 TCGA 项目
# projects <- getGDCprojects()$project_id
# tcga_projects <- projects[grep("^TCGA-", projects)]
# 
# main_dir <- "TCGA_STAR_Counts_Links"
# dir.create(main_dir, showWarnings = FALSE, recursive = TRUE)
# 
# all_links <- list()
# 
# for (proj in tcga_projects) {
#   cat("正在生成链接：", proj, "\n")
#   
#   query <- GDCquery(
#     project = proj,
#     data.category = "Transcriptome Profiling",
#     data.type = "Gene Expression Quantification",
#     workflow.type = "STAR - Counts"
#     # sample.type = "Primary Tumor"   # 如果只需要原发肿瘤，可取消注释
#   )
#   
#   results <- getResults(query)
#   
#   # 生成下载链接
#   results <- results %>%
#     mutate(
#       download_link = paste0("https://api.gdc.cancer.gov/data/", file_id),
#       project = proj
#     )
#   
#   # 保存每个癌症独立的链接文件（推荐）
#   write_csv(results, 
#             file.path(main_dir, paste0(proj, "_STAR_Counts_links.csv")))
#   
#   # 同时合并到一个总文件中
#   cat(proj, "完成，文件数：", nrow(results), "\n")
# }


library(dplyr)
files=list.files("TCGA_STAR_Counts_Links/",full.names = TRUE)
for(tcga_link in files){
  library(dplyr)
  library(readr)
  library(furrr)
  library(progressr)   # 可选：显示进度条
  library(purrr )
  # 1. 读取数据
  # 2. 构建保存路径（保持您想要的文件夹结构）
  # 读取链接文件（请确认路径正确）
  df <- read.csv(tcga_link)
  df <- df %>%
    mutate(
      save_dir = file.path("TCGA_STAR_Counts", 
                           project, 
                           "Transcriptome_Profiling", 
                           "Gene_Expression_Quantification", 
                           file_id),
      save_path = file.path(save_dir, file_name)
    )
  
  # 创建所有目录
  dir.create(df$save_dir[1], recursive = TRUE, showWarnings = FALSE)  # 先创建主目录
  
  # 使用循环下载（带简单进度提示）

  
  # 3. 创建所有目录（提前一次性创建，避免并行冲突）
  unique_dirs <- unique(df$save_dir)
  walk(unique_dirs, ~ dir.create(.x, recursive = TRUE, showWarnings = FALSE))
  
  # 4. 设置并行计划（根据您的电脑配置调整）
  plan(multisession, workers = 16)   # Windows/Mac 推荐 multisession，workers 可改成 4~12
  
  # 5. 并行下载 + 进度显示
  handlers(global = TRUE)   # 启用进度条
  
  cat(paste0("开始并行下载 ",tcga_link, "Counts 数据...\n"))
  
  future_pwalk(df, function(file_id, save_path, file_name, ...) {
    dir.create(dirname(save_path), recursive = TRUE, showWarnings = FALSE)
    
    tryCatch({
      download.file(
        url = paste0("https://api.gdc.cancer.gov/data/", file_id),
        destfile = save_path,
        mode = "wb",
        quiet = TRUE
      )
      cat("✅ 下载完成:", file_name, "\n")
    }, error = function(e) {
      cat("❌ 下载失败:", file_name, "\n")
    })
  }, .progress = TRUE)
  
  cat("TCGA-BRCA 并行下载任务已提交完成！\n")
  
  
  cat("TCGA-BRCA 下载完成！\n")


}
