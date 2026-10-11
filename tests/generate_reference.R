args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2L)
destination <- args[1]
upstream <- normalizePath(args[2])
manifest <- jsonlite::read_json("src/controlchartspy/_vendor/manifest.json")
revision <- system2("git", c("-C", shQuote(upstream), "rev-parse", "HEAD"), stdout = TRUE)
version <- as.character(utils::packageVersion("controlcharts"))
stopifnot(identical(revision, manifest$revision))
stopifnot(version == read.dcf(file.path(upstream, "DESCRIPTION"), fields = "Version")[1])
for (name in names(manifest$assets)) {
  relative <- sub("^inst/", "", manifest$assets[[name]]$source)
  installed <- system.file(relative, package = "controlcharts", mustWork = TRUE)
  vendored <- file.path("src/controlchartspy/_vendor", name)
  stopifnot(identical(
    readBin(installed, "raw", n = file.info(installed)$size),
    readBin(vendored, "raw", n = file.info(vendored)$size)
  ))
}
dir.create(destination, recursive = TRUE, showWarnings = FALSE)

data <- data.frame(
  key = sprintf("2024-%02d-01", 1:8),
  numerator = c(8, 11, 10, 12, 9, 13, 8, 10),
  denominator = c(80, 95, 90, 105, 85, 110, 75, 100),
  sd = c(2, 3, 2, 4, 3, 2, 4, 3)
)
cases <- list()
add_case <- function(name, type, data, settings = list(), columns = list()) {
  input <- c(list(data = as.list(data), keys = "key", numerators = "numerator"),
             columns, settings)
  call_args <- c(list(data = data, keys = quote(key), numerators = quote(numerator)),
                 settings)
  for (column in names(columns)) {
    value <- columns[[column]]
    if (is.list(value)) {
      expression <- as.call(c(list(quote(list)), lapply(value, as.name)))
      call_args[[column]] <- expression
    } else {
      call_args[[column]] <- as.name(value)
    }
  }
  result <- do.call(getExportedValue("controlcharts", type), call_args)
  expected <- list(limits = result$limits, limit_lines = result$limit_lines)
  if (!is.null(result$static_plot)) {
    plot <- result$static_plot
    expected$svg <- controlcharts:::svg_string(plot$svg, plot$width, plot$height)
  }
  expected["indicator_names"] <- list(attr(result$limits, "indicator_names"))
  if (type == "misc") {
    expected$target <- attr(result, "target")
  }
  cases[[name]] <<- list(type = type, input = input, expected = expected)
}

for (type in c("run", "i", "i_m", "i_mm", "mr", "p", "pp", "u", "up",
               "c", "xbar", "s", "g", "t")) {
  columns <- list()
  if (type %in% c("p", "pp", "u", "up", "xbar", "s")) {
    columns$denominators <- "denominator"
  }
  if (type %in% c("xbar", "s")) {
    columns$xbar_sds <- "sd"
  }
  add_case(paste0("spc_", type), "spc", data,
           list(spc_settings = list(chart_type = type),
                return_objs = c("limits", "static_plot")), columns)
}

funnel_data <- data
funnel_data$key <- LETTERS[1:8]
for (type in c("PR", "SR", "RC")) {
  add_case(paste0("funnel_", type), "funnel", funnel_data,
           list(funnel_settings = list(chart_type = type),
                return_objs = c("limits", "limit_lines", "static_plot")),
           list(denominators = "denominator"))
}

add_case("spc_flags", "spc", data,
         list(outlier_settings = list(astronomical = TRUE, shift = TRUE,
                                       trend = TRUE, two_in_three = TRUE),
              return_objs = c("limits", "static_plot")))
add_case("funnel_flags", "funnel", funnel_data,
         list(outlier_settings = list(two_sigma = TRUE, three_sigma = TRUE),
              return_objs = c("limits", "static_plot")),
         list(denominators = "denominator"))

labelled <- data
labelled$label <- c("A & B", "<first>", NA, "Delta", "E", "F", "G", "H")
add_case("spc_labels", "spc", labelled,
         list(title = list(text = "SPC <chart> & limits", subtitle = "A & B"),
              width = 720, height = 480,
              scatter_settings = list(colour = rep(c("#112233", "#334455"), 4)),
              x_axis_settings = list(xlimit_label = "Month & year", xlimit_tick_rotation = 45),
              return_objs = c("limits", "static_plot")),
         list(labels = "label"))
add_case("funnel_labels", "funnel", transform(funnel_data, label = labelled$label),
         list(title = "Funnel <chart> & limits", width = 800, height = 450,
              x_axis_settings = list(xlimit_label = "Population & size"),
              return_objs = c("limits", "static_plot")),
         list(denominators = "denominator", labels = "label"))

add_case("spc_aggregation", "spc", rbind(data, data),
         list(aggregations = list(numerators = "mean"),
              return_objs = c("limits", "static_plot")))
add_case("funnel_aggregation", "funnel", rbind(funnel_data, funnel_data),
         list(return_objs = c("limits", "static_plot")),
         list(denominators = "denominator"))
add_case("spc_phases", "spc", transform(data, phase = rep(c("Before", "After"), each = 4)),
         list(return_objs = c("limits", "static_plot")), list(groupings = "phase"))
add_case("spc_sorted", "spc", data[c(8, 1, 7, 2, 6, 3, 5, 4), ],
         list(return_objs = c("limits", "static_plot")))

grouped <- rbind(transform(data, region = "North", site = "A"),
                 transform(data, region = "South", site = "B", numerator = numerator + 2))
add_case("spc_indicators", "spc", grouped,
         list(spc_settings = list(chart_type = "p"), return_objs = "limits"),
         list(denominators = "denominator", indicators = list(region = "region", site = "site")))

missing_data <- data
missing_data$numerator[3] <- NA_real_
add_case("spc_missing", "spc", missing_data,
         list(return_objs = c("limits", "static_plot")))
add_case("funnel_missing", "funnel", transform(missing_data, key = LETTERS[1:8]),
         list(return_objs = c("limits", "static_plot")), list(denominators = "denominator"))
add_case("funnel_alt_target", "funnel", funnel_data,
         list(line_settings = list(show_alt_target = TRUE, alt_target = 12),
              return_objs = c("limits", "limit_lines", "static_plot")),
         list(denominators = "denominator"))
add_case("spc_alt_target", "spc", data,
         list(line_settings = list(show_alt_target = TRUE, alt_target = 12),
              return_objs = c("limits", "static_plot")))
signal <- data
signal$numerator <- c(rep(10, 7), 100)
add_case("spc_signal", "spc", signal,
         list(outlier_settings = list(astronomical = TRUE, shift = TRUE,
                                       trend = TRUE, two_in_three = TRUE),
              return_objs = c("limits", "static_plot")))

comparison <- data.frame(
  key = rep(LETTERS[1:4], 2),
  indicator = rep(c("Higher is better", "Lower is better"), each = 4),
  numerator = c(80, 20, 24, 30, 4, 20, 24, 30),
  denominator = 100,
  direction = rep(c("increase", "decrease"), each = 4),
  grouping = rep(c("Effectiveness", "Safety"), each = 4)
)
add_case("misc_PR", "misc", comparison,
         list(target = "A", outlier_settings = list(improvement_direction = comparison$direction),
              return_objs = c("limits", "static_plot")),
         list(denominators = "denominator", indicators = "indicator", groupings = "grouping"))
add_case("misc_single", "misc", comparison[1:4, ],
         list(target = "A", width = 720, height = 480,
              title = list(text = "MISC <chart> & scores", subtitle = "One indicator"),
              return_objs = c("limits", "static_plot")),
         list(denominators = "denominator", indicators = "indicator"))

repeated <- comparison[rep(seq_len(nrow(comparison)), each = 2), ]
repeated$numerator <- repeated$numerator / 2
repeated$denominator <- repeated$denominator / 2
repeated$note <- paste0("row-", seq_len(nrow(repeated)))
repeated <- repeated[c(16, 3, 1, 10, 7, 12, 4, 14, 2, 9, 15, 5, 11, 8, 13, 6), ]
add_case("misc_aggregation", "misc", repeated,
         list(target = "A", aggregations = list(tooltips = "last"),
              outlier_settings = list(improvement_direction = repeated$direction, three_sigma = FALSE),
              bar_settings = list(colour_improvement = c("#112233", "#445566")),
              title = "Aggregated indicators", return_objs = c("limits", "static_plot")),
         list(denominators = "denominator", indicators = "indicator", groupings = "grouping",
              tooltips = list(Note = "note")))

mixed <- data.frame(
  key = rep(LETTERS[1:4], 3),
  indicator = rep(c("Proportion", "Ratio", "Rate"), each = 4),
  numerator = c(8, 5, 4, 6, 8, 12, 11, 9, 4, 8, 6, 10),
  denominator = rep(c(10, 10, 1000), each = 4),
  chart_type = rep(c("PR", "SR", "RC"), each = 4),
  multiplier = rep(c(1, 1, 1000), each = 4),
  direction = rep(c("increase", "decrease", "decrease"), each = 4)
)
mixed <- mixed[c(6, 12, 3, 1, 9, 5, 10, 7, 4, 11, 2, 8), ]
add_case("misc_mixed", "misc", mixed,
         list(target = "A",
              funnel_settings = list(chart_type = mixed$chart_type, multiplier = mixed$multiplier),
              outlier_settings = list(improvement_direction = mixed$direction),
              return_objs = c("limits", "static_plot")),
         list(denominators = "denominator", indicators = "indicator"))
add_case("misc_rate_suffix", "misc", transform(comparison[1:4, ], denominator = 1000),
         list(target = "A", funnel_settings = list(multiplier = 1000, perc_labels = "No", sig_figs = 3),
              return_objs = c("limits", "static_plot")),
         list(denominators = "denominator", indicators = "indicator"))
partial <- comparison
partial$key[5] <- "E"
add_case("misc_partial", "misc", partial,
         list(target = "A", return_objs = c("limits", "static_plot")),
         list(denominators = "denominator", indicators = "indicator"))

for (name in names(cases)) {
  jsonlite::write_json(cases[[name]], file.path(destination, paste0(name, ".json")),
                       auto_unbox = TRUE, dataframe = "rows", null = "null", na = "null",
                       digits = NA, pretty = TRUE)
}
jsonlite::write_json(
  list(spc = controlcharts::spc_default_settings(),
       funnel = controlcharts::funnel_default_settings(),
       misc = controlcharts::misc_default_settings()),
  file.path(destination, "defaults.json"), auto_unbox = TRUE, null = "null",
  digits = NA, pretty = TRUE
)
jsonlite::write_json(
  list(repository = manifest$repository, revision = revision,
       package_version = version, r_version = R.version.string,
       assets = manifest$assets),
  file.path(dirname(destination), "reference_manifest.json"),
  auto_unbox = TRUE, pretty = TRUE
)
cat("Generated", length(cases), "reference cases\n")
