document.addEventListener('DOMContentLoaded', function(event) {
    draw_answer_box();
})

var draw_answer_box = function() {
    var canvas = document.getElementById('answer_box');
    var drawing = new AnswerBoxesDrawingContext(canvas);
    drawing.draw(20, 3);
}

var AnswerBoxesDrawingContext = function(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");

    this.draw = function(num_questions, num_choices) {
        var boxes = new AnswerBoxes(num_questions, num_choices);
        boxes.draw(this.ctx);
    }

    this.clear = function() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
}

var AnswerBoxes = function(num_questions, num_choices) {
    this.geometry = GeometryAnalyzer.best_geometry(num_questions, num_choices);

    this.draw = function(ctx) {
        var cell_size = GeometryAnalyzer.cell_size(this.geometry, ctx.canvas.width, ctx.canvas.height);
        var top_left_corner = GeometryAnalyzer.top_left_corner(this.geometry, cell_size, ctx.canvas.width, ctx.canvas.height);
        for (var i = 0; i < this.geometry.num_tables; i++) {
            var extra_bottom_line = this.geometry.questions_per_table[i] < this.geometry.num_rows;
            var box = new AnswerBox(this.geometry.questions_per_table[i], num_choices, extra_bottom_line);
            var box_top_left_corner = {
                x: top_left_corner.x + i * (num_choices + 1) * cell_size.width,
                y: top_left_corner.y
            };
            box.draw(ctx, box_top_left_corner, cell_size);
        }
    }
}

var AnswerBox = function(num_questions, num_choices, extra_bottom_line) {
    this.num_questions = num_questions;
    this.num_choices = num_choices;
    this.extra_bottom_line = extra_bottom_line;

    this.draw = function(ctx, top_left_corner, cell_size) {
        ctx.beginPath();
        var top_y = top_left_corner.y + cell_size.height;
        var bottom_y = top_y + cell_size.height * this.num_questions;
        var left_x = top_left_corner.x + cell_size.width;
        var right_x = left_x + cell_size.width * this.num_choices;
        // Draw vertical lines:
        for (var i = 0; i < this.num_choices + 1; i++) {
            var x = left_x + i * cell_size.width;
            ctx.moveTo(x, top_y);
            ctx.lineTo(x, bottom_y);
        }
        // Draw horizontal lines
        var num_lines;
        if (!this.extra_bottom_line) {
            num_lines = this.num_questions + 1;
        } else {
            // Extra line because other boxes have one row more
            num_lines = this.num_questions + 2;
        }
        for (var i = 0; i < num_lines; i++) {
            var y = top_y + i * cell_size.height;
            ctx.moveTo(left_x, y);
            ctx.lineTo(right_x, y);
        }
       ctx.stroke();
    }
}

var GeometryAnalyzer = {
    // default cell aspect ratio: cell width / cell height = 1.5
    default_cell_ratio: 1.5,

    best_geometry: function(num_questions, num_choices) {
        var geometries = [];
        for (var i = 1; i < 5; i++) {
            geometries.push(this.fit(num_questions, num_choices, i));
        }
        return this.choose_geometry(geometries);
    },

    cell_size: function(geometry, canvas_width, canvas_height) {
        var usable_width = 0.95 * canvas_width; // 2.5% left and right margins
        var usable_height = 0.95 * canvas_height; // 2.5% top and bottom margin
        var cell_width = ~~(usable_width / geometry.total_columns);
        var cell_height = ~~(cell_width / geometry.cell_ratio);
        if (cell_height * geometry.total_rows > usable_height) {
            cell_height = ~~(usable_height / geometry.total_rows);
            cell_width = ~~(cell_height * geometry.cell_ratio);
        }
        return {
            width: cell_width,
            height: cell_height
        };
    },

    top_left_corner: function(geometry, cell_size, canvas_width, canvas_height) {
        return {
            x: ~~((canvas_width - cell_size.width * geometry.total_columns) / 2),
            y: ~~((canvas_height - cell_size.height * geometry.total_rows) / 2)
        };
    },

    fit: function(num_questions, num_choices, num_tables) {
        var g = {};
        g.num_tables = num_tables;
        g.questions_per_table = this.questions_per_table(num_questions, num_tables);
        g.num_rows = Math.max(...g.questions_per_table);
        g.num_columns = num_tables * num_choices;
        g.total_rows = g.num_rows + 3; // header line + 2 infobits lines
        g.total_columns = g.num_columns + num_tables; // one question number per table
        var actual_ratio = this.default_cell_ratio * g.num_columns / g.num_rows;
        // no dimension should be more than 30% larger than the other
        if (actual_ratio > 1.3) {
            // Cells are too wide
            g.cell_ratio = 1.3 * g.num_rows / g.num_columns;
        } else if (actual_ratio < 0.769) {
            // Cells are too heigh
            g.cell_ratio = 0.769 * g.num_rows / g.num_columns;
        } else {
            // The default aspect ratio works fine
            g.cell_ratio = this.default_cell_ratio;
        }
        return g;
    },

    questions_per_table: function(num_questions, num_tables) {
        var questions_per_table = []
        var q = ~~(num_questions / num_tables)
        var remainder = num_questions % num_tables
        for (var i = 0; i < num_tables; i++) {
            if (remainder > 0) {
                questions_per_table.push(q + 1);
                remainder--;
            } else {
                questions_per_table.push(q);
            }
        }
        return questions_per_table;
    },

    choose_geometry: function(geometries) {
        var i;
        var best_dist = Infinity;
        var best_geometry;
        for (i in geometries) {
            g = geometries[i];
            dist = Math.abs(g.cell_ratio - this.default_cell_ratio)
            if (dist < best_dist) {
                best_dist = dist;
                best_geometry = g;
            } else {
                // Ratios go from higher to lower values.
                // Once a geometry is farther away from the default than the previous one,
                // iteration can stop.
                break;
            }
        }
        return best_geometry;
    }
}