(function () {
    const dataNode = document.getElementById("statistica-data");
    const canvas = document.getElementById("statChart");
    if (!dataNode || !canvas) {
        return;
    }

    const data = JSON.parse(dataNode.textContent);
    const colors = ["#206bc4", "#2fb344", "#f76707", "#ae3ec9", "#d63939", "#0ca678", "#4263eb"];
    const weekdays = ["dom", "lun", "mar", "mer", "gio", "ven", "sab"];
    const metricLabels = {
        numero: "Numero riparazioni",
        prezzo_pubblico: "Prezzo al pubblico",
        prezzo_pagato: "Prezzo pagato",
        costo_totale: "Costo totale",
    };

    let metrica = "numero";
    let highlighted = null;
    const points = [];

    const tooltip = document.getElementById("statTooltip");
    const titleNode = document.getElementById("statChartTitle");
    const legend = document.getElementById("statLegend");
    const totals = document.getElementById("statTotali");
    const table = document.getElementById("statTable");
    const emptyNode = document.getElementById("statEmpty");

    function colorFor(index) {
        return colors[index % colors.length];
    }

    function isMoney() {
        return metrica !== "numero";
    }

    function formatItalian(value, decimals) {
        const number = Number(value) || 0;
        const negative = number < 0;
        const absolute = Math.abs(number);
        const fixed = absolute.toFixed(decimals);
        const parts = fixed.split(".");
        const integer = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        const text = decimals > 0 ? integer + "," + parts[1] : integer;
        return (negative ? "-" : "") + text;
    }

    function formatValue(value) {
        if (!isMoney()) {
            return formatItalian(Math.round(Number(value) || 0), 0);
        }
        return formatItalian(value, 2) + " €";
    }

    function weekdayName(index) {
        const start = new Date(String(data.dal || "") + "T12:00:00");
        if (Number.isNaN(start.getTime())) {
            return "";
        }
        const day = new Date(start.getTime());
        day.setDate(start.getDate() + index);
        return weekdays[day.getDay()];
    }

    function seriesValues(series) {
        return series[metrica] || [];
    }

    function isDimmed(index) {
        return highlighted !== null && highlighted !== index;
    }

    function sum(values) {
        return (values || []).reduce(function (total, value) {
            return total + (Number(value) || 0);
        }, 0);
    }

    function renderTotals() {
        if (!totals) {
            return;
        }
        totals.innerHTML = "";
        let grand = 0;
        data.series.forEach(function (series, index) {
            const value = sum(seriesValues(series));
            grand += value;
            const col = document.createElement("div");
            col.className = "col-sm-6 col-lg-3";
            col.innerHTML =
                '<div class="card"><div class="card-body">' +
                '<div class="text-secondary small">' + series.label + "</div>" +
                '<div class="h2 mb-0">' + formatValue(value) + "</div>" +
                "</div></div>";
            const swatch = document.createElement("span");
            swatch.className = "st-stat-swatch me-1";
            swatch.style.background = colorFor(index);
            col.querySelector(".text-secondary").prepend(swatch);
            totals.appendChild(col);
        });
        if (isMoney()) {
            grand = Math.round(grand * 100) / 100;
        }
        const totalCol = document.createElement("div");
        totalCol.className = "col-sm-6 col-lg-3 ms-lg-auto";
        totalCol.innerHTML =
            '<div class="card"><div class="card-body">' +
            '<div class="text-secondary small">Totale</div>' +
            '<div class="h2 mb-0">' + formatValue(grand) + "</div>" +
            "</div></div>";
        totals.appendChild(totalCol);
    }

    function renderLegend() {
        if (!legend) {
            return;
        }
        legend.innerHTML = "";
        data.series.forEach(function (series, index) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = isDimmed(index) ? "is-muted" : "";
            button.innerHTML =
                '<span class="st-stat-swatch" style="background:' + colorFor(index) + '"></span>' +
                series.label;
            button.addEventListener("click", function () {
                highlighted = highlighted === index ? null : index;
                render();
            });
            legend.appendChild(button);
        });
    }

    function rowTotal(position) {
        return data.series.reduce(function (total, series) {
            return total + (Number(seriesValues(series)[position]) || 0);
        }, 0);
    }

    function renderTable() {
        if (!table) {
            return;
        }
        const head = ["<tr><th>Periodo</th>"];
        data.series.forEach(function (series) {
            head.push("<th class=\"text-end\">" + series.label + "</th>");
        });
        head.push("<th class=\"text-end\">Totale</th></tr>");
        const body = data.labels.map(function (label, position) {
            const period = data.granularita === "giorno" ? weekdayName(position) + " " + label : label;
            const cells = ["<td>" + period + "</td>"];
            data.series.forEach(function (series) {
                cells.push("<td class=\"text-end\">" + formatValue(seriesValues(series)[position]) + "</td>");
            });
            let total = rowTotal(position);
            if (isMoney()) {
                total = Math.round(total * 100) / 100;
            }
            cells.push("<td class=\"text-end fw-bold\">" + formatValue(total) + "</td>");
            return "<tr>" + cells.join("") + "</tr>";
        });
        const foot = ["<th>Totale</th>"];
        let grand = 0;
        data.series.forEach(function (series) {
            const value = sum(seriesValues(series));
            grand += value;
            foot.push("<td class=\"text-end\">" + formatValue(value) + "</td>");
        });
        if (isMoney()) {
            grand = Math.round(grand * 100) / 100;
        }
        foot.push("<td class=\"text-end\">" + formatValue(grand) + "</td>");
        table.innerHTML =
            "<thead>" + head.join("") + "</thead>" +
            "<tbody>" + body.join("") + "</tbody>" +
            "<tfoot><tr>" + foot.join("") + "</tr></tfoot>";
    }

    function niceMax(value) {
        if (value <= 0) {
            return 1;
        }
        const power = Math.pow(10, Math.floor(Math.log10(value)));
        const step = power / 2;
        return Math.ceil(value / step) * step;
    }

    function draw() {
        const wrap = canvas.parentElement;
        const width = wrap.clientWidth;
        const height = wrap.clientHeight;
        const ratio = window.devicePixelRatio || 1;
        canvas.width = Math.max(1, Math.floor(width * ratio));
        canvas.height = Math.max(1, Math.floor(height * ratio));
        const ctx = canvas.getContext("2d");
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        ctx.clearRect(0, 0, width, height);
        points.length = 0;

        const count = Math.max(1, data.labels.length);
        const isDay = data.granularita === "giorno";
        ctx.font = "12px sans-serif";
        const sampleLabel = data.labels[0] || "";
        const labelWidth = ctx.measureText(sampleLabel).width;
        const pad = {
            top: 16,
            right: 16,
            bottom: isDay ? 52 : 36,
            left: 72,
        };
        const plotW = Math.max(1, width - pad.left - pad.right);
        const plotH = Math.max(1, height - pad.top - pad.bottom);
        let max = 0;
        data.series.forEach(function (series, index) {
            if (isDimmed(index)) {
                return;
            }
            seriesValues(series).forEach(function (value) {
                max = Math.max(max, Number(value) || 0);
            });
        });
        if (max === 0) {
            data.series.forEach(function (series) {
                seriesValues(series).forEach(function (value) {
                    max = Math.max(max, Number(value) || 0);
                });
            });
        }
        max = niceMax(max);
        const groupWidth = plotW / count;

        ctx.strokeStyle = "#e6e8eb";
        ctx.fillStyle = "#667085";
        ctx.font = "12px sans-serif";
        ctx.lineWidth = 1;
        for (let tick = 0; tick <= 4; tick += 1) {
            const value = (max / 4) * tick;
            const y = pad.top + plotH - (value / max) * plotH;
            ctx.beginPath();
            ctx.moveTo(pad.left, y);
            ctx.lineTo(width - pad.right, y);
            ctx.stroke();
            ctx.textAlign = "right";
            ctx.textBaseline = "middle";
            const tickLabel = isMoney()
                ? formatItalian(value, 0)
                : formatItalian(Math.round(value), 0);
            ctx.fillText(tickLabel, pad.left - 8, y);
        }

        const labelEvery = isDay ? 1 : Math.max(1, Math.ceil((labelWidth + 8) / groupWidth));
        const axisY = pad.top + plotH;
        ctx.fillStyle = "#667085";
        ctx.strokeStyle = "#d0d5dd";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        data.labels.forEach(function (label, index) {
            if (index % labelEvery !== 0 && index !== count - 1) {
                return;
            }
            const x = pad.left + index * groupWidth + groupWidth / 2;
            ctx.beginPath();
            ctx.moveTo(x, axisY);
            ctx.lineTo(x, axisY + 4);
            ctx.stroke();
            if (isDay) {
                let fontSize = 12;
                ctx.font = fontSize + "px sans-serif";
                while (fontSize > 9 && ctx.measureText(label).width > groupWidth - 2) {
                    fontSize -= 1;
                    ctx.font = fontSize + "px sans-serif";
                }
                ctx.fillStyle = "#1d2733";
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                ctx.fillText(label, x, axisY + 6);
                ctx.fillStyle = "#667085";
                ctx.font = Math.max(9, fontSize - 1) + "px sans-serif";
                ctx.fillText(weekdayName(index), x, axisY + 6 + fontSize + 2);
                return;
            }
            ctx.fillText(label, x, axisY + 8);
        });

        const seriesCount = Math.max(1, data.series.length);
        const barGap = seriesCount > 1 && groupWidth > 28 ? 2 : 0;
        let barWidth = (groupWidth * 0.78 - barGap * (seriesCount - 1)) / seriesCount;
        if (barWidth < 1) {
            barWidth = (groupWidth * 0.9) / seriesCount;
        }
        const groupOrigin = (groupWidth - (barWidth * seriesCount + barGap * (seriesCount - 1))) / 2;

        data.series.forEach(function (series, seriesIndex) {
            const values = seriesValues(series);
            const coords = values.map(function (value, index) {
                const number = Number(value) || 0;
                const barH = (number / max) * plotH;
                const x = pad.left + index * groupWidth + groupOrigin + seriesIndex * (barWidth + barGap);
                const y = pad.top + plotH - barH;
                return {
                    x: pad.left + index * groupWidth + groupWidth / 2,
                    y: y,
                    barX: x,
                    barW: barWidth,
                    barH: barH,
                    value: number,
                    label: data.labels[index],
                };
            });
            points.push(coords);
            ctx.globalAlpha = isDimmed(seriesIndex) ? 0.18 : 1;
            ctx.fillStyle = colorFor(seriesIndex);
            coords.forEach(function (point) {
                if (point.barH <= 0) {
                    return;
                }
                const radius = Math.min(3, point.barW / 2, point.barH / 2);
                ctx.beginPath();
                if (typeof ctx.roundRect === "function" && radius > 0) {
                    ctx.roundRect(point.barX, point.y, point.barW, point.barH, [radius, radius, 0, 0]);
                } else {
                    ctx.rect(point.barX, point.y, point.barW, point.barH);
                }
                ctx.fill();
            });
            ctx.globalAlpha = 1;
        });
    }

    function render() {
        if (titleNode) {
            titleNode.textContent = metricLabels[metrica];
        }
        const hasValues = data.series.some(function (series) {
            return sum(series.numero) > 0;
        });
        if (emptyNode) {
            emptyNode.hidden = hasValues;
        }
        renderTotals();
        renderLegend();
        renderTable();
        draw();
    }

    function nearestIndex(offsetX) {
        if (!points.length || !points[0].length) {
            return -1;
        }
        let best = 0;
        let bestDist = Infinity;
        points[0].forEach(function (point, index) {
            const dist = Math.abs(point.x - offsetX);
            if (dist < bestDist) {
                best = index;
                bestDist = dist;
            }
        });
        const limit = points[0].length > 1
            ? Math.abs(points[0][1].x - points[0][0].x) / 2
            : 48;
        return bestDist > limit ? -1 : best;
    }

    canvas.addEventListener("mousemove", function (event) {
        const rect = canvas.getBoundingClientRect();
        const index = nearestIndex(event.clientX - rect.left);
        if (index < 0) {
            tooltip.hidden = true;
            return;
        }
        const lines = [
            data.granularita === "giorno"
                ? weekdayName(index) + " " + data.labels[index]
                : data.labels[index],
        ];
        data.series.forEach(function (series, seriesIndex) {
            if (isDimmed(seriesIndex)) {
                return;
            }
            lines.push(series.label + ": " + formatValue(seriesValues(series)[index]));
        });
        tooltip.innerHTML = lines.join("<br>");
        let top = points[0][index].y;
        data.series.forEach(function (series, seriesIndex) {
            if (isDimmed(seriesIndex) || !points[seriesIndex]) {
                return;
            }
            top = Math.min(top, points[seriesIndex][index].y);
        });
        tooltip.hidden = false;
        tooltip.style.left = points[0][index].x + "px";
        tooltip.style.top = Math.max(28, top) + "px";
    });
    canvas.addEventListener("mouseleave", function () {
        tooltip.hidden = true;
    });

    document.querySelectorAll("#statMetriche [data-metrica]").forEach(function (button) {
        button.addEventListener("click", function () {
            metrica = button.getAttribute("data-metrica");
            document.querySelectorAll("#statMetriche [data-metrica]").forEach(function (item) {
                const active = item === button;
                item.classList.toggle("btn-primary", active);
                item.classList.toggle("btn-outline-secondary", !active);
            });
            render();
        });
    });

    document.querySelectorAll("[data-stat-export]").forEach(function (link) {
        link.addEventListener("click", function () {
            const params = new URLSearchParams();
            const granularita = document.querySelector('input[name="g"]');
            params.set("formato", link.getAttribute("data-stat-export"));
            params.set("g", granularita ? granularita.value : "mese");
            params.set("dal", document.getElementById("statDal").value);
            params.set("al", document.getElementById("statAl").value);
            link.search = params.toString();
        });
    });

    window.addEventListener("resize", draw);
    render();
})();
