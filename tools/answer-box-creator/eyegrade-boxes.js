document.addEventListener('DOMContentLoaded', function(event) {
    document.getElementById("config_form").elements["num_questions"].onchange = form_changed;
    document.getElementById("config_form").elements["num_choices"].onchange = form_changed;
    document.getElementById("config_form").elements["print_model_letter"].onchange = form_changed;
    document.getElementById("config_form").elements["num_id_digits"].onchange = form_changed;
    document.getElementById("config_form").elements["id_box_label"].onchange = form_changed;
    document.getElementById("config_form").elements["id_box_label"].oninput = form_changed;
    document.getElementById("config_form").elements["read_id"].onchange = read_id_changed;
    document.getElementById("download").onclick = download_images;
    form_changed();
})

var fields_state_read_id = {
    id_num_digits: 8,
    id_box_label: "Id:"
}

var form_changed = function() {
    var num_questions = Number(document.getElementById("config_form").elements["num_questions"].value);
    var num_choices = Number(document.getElementById("config_form").elements["num_choices"].value);
    var num_id_digits = Number(document.getElementById("config_form").elements["num_id_digits"].value);
    var id_box_label = document.getElementById("config_form").elements["id_box_label"].value;
    var print_model_letter = document.getElementById("config_form").elements["print_model_letter"].checked;
    var exam_structure = {
        num_questions: num_questions,
        num_choices: num_choices,
        num_id_digits: num_id_digits,
        id_box_label: id_box_label,
        print_model_letter: print_model_letter
    }
    draw_answer_box(exam_structure);
}

var read_id_changed = function() {
    var field_num_id_digits = document.getElementById("config_form").elements["num_id_digits"];
    var field_id_box_label = document.getElementById("config_form").elements["id_box_label"];
    var read_student_id = document.getElementById("config_form").elements["read_id"].checked;
    if (read_student_id) {
        field_num_id_digits.disabled = false;
        field_id_box_label.disabled = false;
        field_num_id_digits.value = fields_state_read_id.id_num_digits;
        field_id_box_label.value = fields_state_read_id.id_box_label;
    } else {
        field_num_id_digits.disabled = true;
        field_id_box_label.disabled = true;
        fields_state_read_id.id_num_digits = field_num_id_digits.value;
        fields_state_read_id.id_box_label = field_id_box_label.value;
        field_num_id_digits.value = 0;
        field_id_box_label.value = "";
    }
    form_changed();
}

var download_images = function() {
    var canvas = document.getElementById('answer_box');
    var data_url = canvas.toDataURL();
    var png_data = data_url.substring(data_url.indexOf('base64,') + 'base64,'.length);
    var zip = new JSZip();
    var img = zip.folder("images");
    img.file("answer-box-A.png", png_data, {base64: true});
    zip.generateAsync({type:"blob"})
        .then(function(content) {
            // see FileSaver.js
            saveAs(content, "answer-boxes.zip");
    });
}

var draw_answer_box = function(exam_structure) {
    var canvas = document.getElementById('answer_box');
    drawing_context = new AnswerBoxesDrawingContext(
        canvas,
        exam_structure.num_questions,
        exam_structure.num_choices,
        exam_structure.num_id_digits,
        exam_structure.id_box_label);
    drawing_context.clear();
    drawing_context.draw("A", exam_structure.print_model_letter);
}

var Defaults = {
    // default cell aspect ratio: cell width / cell height = 1.5
    cell_ratio: 1.5,
    usable_width: 0.96, // 2% left and right margins
    usable_height: 0.96, // 2% top and bottom margins
    id_bottom_line_dist: 0.6 // 1.8 * cell_height above top answer table line
}

var AnswerBoxesDrawingContext = function(canvas, num_questions, num_choices, num_id_digits, id_box_label) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.boxes = new AnswerBoxes(num_questions, num_choices, num_id_digits, id_box_label);

    this.draw = function(model_letter, print_model_letter) {
        this.ctx.fillStyle = 'white';
        this.ctx.fillRect(0, 0, canvas.width, canvas.height);
        this.ctx.fillStyle = 'black';
        this.boxes.draw(this.ctx, model_letter, print_model_letter);
    }

    this.clear = function() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
}

var AnswerBoxes = function(num_questions, num_choices, num_id_digits, id_box_label) {
    this.id_box_label = id_box_label;
    this.geometry = GeometryAnalyzer.best_geometry(num_questions, num_choices, num_id_digits);

    this.draw = function(ctx, model_letter, print_model_letter) {
        var cell_size = this.geometry.cell_size(ctx.canvas.width, ctx.canvas.height);
        var top_left_corner = this.geometry.top_left_corner(cell_size, ctx.canvas.width, ctx.canvas.height);
        var num_digits_question_num = this.compute_num_digits_question_num();
        var first_question_number = 1;
        var infobits = this.infobits(model_letter);
        for (var i = 0; i < this.geometry.num_tables; i++) {
            var extra_bottom_line = this.geometry.questions_per_table[i] < this.geometry.num_rows;
            var box = new AnswerBox(this.geometry.questions_per_table[i], num_choices, first_question_number, num_digits_question_num, extra_bottom_line);
            var box_top_left_corner = {
                x: top_left_corner.x + i * (num_choices + 1) * cell_size.width,
                y: top_left_corner.y
            };
            var infobits_fragment = infobits.substring(i * num_choices, (i + 1) * num_choices);
            box.draw(ctx, box_top_left_corner, cell_size, infobits_fragment);
            first_question_number += this.geometry.questions_per_table[i];
        }
        if (this.geometry.num_id_digits > 0) {
            var id_box = new IdBox(this.geometry.num_id_digits);
            var id_cell_size = this.geometry.id_cell_size(cell_size);
            var id_top_left_corner = this.geometry.id_top_left_corner(cell_size, id_cell_size, top_left_corner, ctx.canvas.width);
            id_box.draw(ctx, id_top_left_corner, id_cell_size, this.id_box_label);
        }
        if (print_model_letter) {
            ctx.textAlign = "right";
            ctx.font = "10 px sans-serif";
            ctx.fillText(model_letter, ctx.canvas.width - 10, ctx.canvas.height - 10, 8);
        }
    }

    this.infobits = function(model_letter) {
        var base_code = this.infobits_table[model_letter.charCodeAt(0) - 65];
        var code = base_code;
        while (code.length < this.geometry.num_columns) {
            code += base_code;
        }
        return code.substring(0, this.geometry.num_columns);
    }

    this.compute_num_digits_question_num = function() {
        if (this.geometry.num_questions < 10) {
            return 1;
        } else if (this.geometry.num_questions < 100) {
            return 2;
        } else {
            return 3;
        }
    }

    this.infobits_table = [
        "DDDU",
        "UDDD",
        "DUDD",
        "UUDU",
        "DDUD",
        "UDUU",
        "DUUU",
        "UUUD"
    ]
}

var IdBox = function(num_id_digits) {
    this.num_id_digits = num_id_digits;

    this.draw = function(ctx, top_left_corner, id_cell_size, label) {
        var bottom_right_corner = {
            x: top_left_corner.x + this.num_id_digits * id_cell_size.width,
            y: top_left_corner.y + id_cell_size.height
        }
        ctx.beginPath();
        ctx.moveTo(top_left_corner.x, top_left_corner.y);
        ctx.lineTo(bottom_right_corner.x, top_left_corner.y);
        ctx.lineTo(bottom_right_corner.x, bottom_right_corner.y);
        ctx.lineTo(top_left_corner.x, bottom_right_corner.y);
        for (var i = 0; i < this.num_id_digits; i++) {
            var x = top_left_corner.x + i * id_cell_size.width;
            ctx.moveTo(x, top_left_corner.y);
            ctx.lineTo(x, bottom_right_corner.y);
        }
        ctx.stroke();
        if (label) {
            this.draw_label(ctx, top_left_corner, id_cell_size, label);
        }
    }

    this.draw_label = function(ctx, top_left_corner, id_cell_size, label) {
        var font_size = 0.8 * id_cell_size.height;
        ctx.textAlign = "right";
        ctx.font = font_size + "px sans-serif";
        var offset = {
            x: - ~~(0.3 * id_cell_size.width),
            y: ~~(0.9 * id_cell_size.height)
        }
        var x = top_left_corner.x + offset.x;
        var y = top_left_corner.y + offset.y;
        ctx.fillText(label, x, y);
    }
}

var AnswerBox = function(num_questions, num_choices, first_question_number, num_digits_question_num, extra_bottom_line) {
    this.num_questions = num_questions;
    this.num_choices = num_choices;
    this.first_question_number = first_question_number;
    this.num_digits_question_num = num_digits_question_num;
    this.extra_bottom_line = extra_bottom_line;

    this.draw = function(ctx, top_left_corner, cell_size, infobits_fragment) {
        var bottom_right_corner = {
            x: top_left_corner.x + (this.num_choices + 1) * cell_size.width,
            y: top_left_corner.y + (this.num_questions + 3) * cell_size.height
        }
        var left_x = top_left_corner.x + cell_size.width;
        var right_x = left_x + cell_size.width * this.num_choices;
        var top_y = top_left_corner.y + cell_size.height;
        var bottom_y = top_y + cell_size.height * this.num_questions;
        this.draw_lines(ctx, cell_size, left_x, right_x, top_y, bottom_y);
        this.draw_question_numbers(ctx, cell_size, top_left_corner);
        this.draw_choice_letters(ctx, cell_size, top_left_corner);
        this.draw_infobits(ctx, cell_size, top_left_corner, infobits_fragment);
        //this.debug_draw_frame(ctx, top_left_corner, bottom_right_corner);
    }

    this.draw_lines = function(ctx, cell_size, left_x, right_x, top_y, bottom_y) {
        ctx.beginPath();
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

    this.draw_question_numbers = function(ctx, cell_size, top_left_corner) {
        var font_size = this.font_size(cell_size);
        ctx.textAlign = "right";
        ctx.font = font_size + "px sans-serif";
        var offset = {
            x: ~~(0.9 * cell_size.width),
            y: ~~(0.9 * cell_size.height)
        }
        for (var i = 1; i <= this.num_questions; i++) {
            var question_num = this.first_question_number + i - 1;
            var x = top_left_corner.x + offset.x;
            var y = top_left_corner.y + offset.y + cell_size.height * i;
            ctx.fillText(question_num.toString(), x, y, 0.8 * cell_size.width);
        }
    }

    this.draw_choice_letters = function(ctx, cell_size, top_left_corner) {
        var font_size = this.font_size(cell_size);
        ctx.textAlign = "center";
        ctx.font = font_size + "px sans-serif";
        var offset = {
            x: ~~(0.5 * cell_size.width),
            y: ~~(0.9 * cell_size.height)
        }
        for (var i = 1; i <= this.num_choices; i++) {
            var letter_num = 64 + i; // i=1 for 'A'
            var x = top_left_corner.x + offset.x + cell_size.width * i;
            var y = top_left_corner.y + offset.y;
            ctx.fillText(String.fromCharCode(letter_num), x, y, 0.8 * cell_size.width);
        }
    }

    this.debug_draw_frame = function(ctx, top_left_corner, bottom_right_corner) {
        var previous_style = ctx.strokeStyle;
        ctx.strokeStyle = "red";
        ctx.beginPath();
        ctx.moveTo(top_left_corner.x, top_left_corner.y);
        ctx.lineTo(bottom_right_corner.x, top_left_corner.y);
        ctx.lineTo(bottom_right_corner.x, bottom_right_corner.y);
        ctx.lineTo(top_left_corner.x, bottom_right_corner.y);
        ctx.lineTo(top_left_corner.x, top_left_corner.y);
        ctx.stroke();
        ctx.strokeStyle = previous_style;
    }

    this.draw_infobits = function(ctx, cell_size, top_left_corner, infobits_fragment) {
        var y_up = ~~(top_left_corner.y + (this.num_questions + 1) * cell_size.height + 0.2 * cell_size.height);
        var y_down = y_up + cell_size.height;
        var size = ~~(0.6 * cell_size.height);
        var x_base = ~~(top_left_corner.x + (cell_size.width - size) / 2);
        for (var i = 0; i < this.num_choices; i++) {
            var x = x_base + (i + 1) * cell_size.width;
            var y;
            if (infobits_fragment.charAt(i) === "U") {
                y = y_up;
            } else {
                y = y_down;
            }
            ctx.fillRect(x, y, size, size);
        }
    }

    this.font_size = function(cell_size) {
        var size_for_width = ~~(cell_size.width / this.num_digits_question_num);
        var size_for_height = cell_size.height;
        return Math.min(size_for_width, size_for_height);
    }
}

var Geometry = function(num_questions, num_choices, num_tables, num_id_digits) {
    this.compute_cell_ratio = function() {
        var actual_ratio = Defaults.cell_ratio * this.num_columns / this.num_rows;
        // no dimension should be more than 30% larger than the other
        if (actual_ratio > 1.3) {
            // Cells are too wide
            return 1.3 * this.num_rows / this.num_columns;
        } else if (actual_ratio < 0.769) {
            // Cells are too heigh
            return 0.769 * this.num_rows / this.num_columns;
        } else {
            // The default aspect ratio works fine
            return Defaults.cell_ratio;
        }
    }

    this.compute_id_cell_ratio = function() {
        // By default, square digit cells as heigh as answer table rows (ratio 1.0)
        // Returns the ratio cell_height / id_cell_height
        if (this.num_id_digits < 1) {
            // No id box will be printed
            return 0.0;
        }
        var id_cells_width = this.num_id_digits;
        var horizontal_lines_width = this.num_columns * this.cell_ratio;
        var horizontal_ratio = horizontal_lines_width / id_cells_width;
        if (horizontal_ratio > 1.3) {
            return 1.3 / horizontal_ratio;
        } else if (horizontal_ratio < 0.769) {
            //return horizontal_lines_width / id_cells_width / 0.769;
            return 0.769 / horizontal_ratio;
        } else {
            return 1.0;
        }
    }

    this.compute_questions_per_table = function() {
        var questions_per_table = []
        var q = ~~(this.num_questions / this.num_tables)
        var remainder = this.num_questions % this.num_tables
        for (var i = 0; i < this.num_tables; i++) {
            if (remainder > 0) {
                questions_per_table.push(q + 1);
                remainder--;
            } else {
                questions_per_table.push(q);
            }
        }
        return questions_per_table;
    }

    this.num_questions = num_questions;
    this.num_choices = num_choices;
    this.num_tables = num_tables;
    this.questions_per_table = this.compute_questions_per_table();
    this.num_rows = Math.max(...this.questions_per_table);
    this.num_columns = num_tables * num_choices;
    this.total_rows = this.num_rows + 3; // header line + 2 infobits lines
    this.total_columns = this.num_columns + num_tables; // one question number per table
    this.cell_ratio = this.compute_cell_ratio();
    this.num_id_digits = num_id_digits;
    this.id_cell_ratio = this.compute_id_cell_ratio();

    this.cell_size = function(canvas_width, canvas_height) {
        var usable_width = Defaults.usable_width * canvas_width;
        var usable_height = Defaults.usable_height * canvas_height;
        var cell_width;
        var cell_height;
        // First, adjust width and forget about height
        if (this.total_columns * this.cell_ratio >= this.num_id_digits * this.id_cell_ratio) {
            // answer boxes are wider than the id box
            cell_width = ~~(usable_width / this.total_columns);
            cell_height = ~~(cell_width / this.cell_ratio);
        } else {
            // the id box is wider than answer tables
            var id_cell_width = ~~(usable_width / this.num_id_digits);
            cell_height = ~~(this.id_cell_ratio * id_cell_width);
            cell_width = ~~(cell_height * this.cell_ratio);
        }
        // Now, adjust to height if needed
        var total_height = this.total_rows * cell_height;
        if (this.num_id_digits > 0) {
            total_height += Defaults.id_bottom_line_dist * cell_height + ~~(cell_height / this.id_cell_ratio);
        }
        if (total_height > usable_height) {
            var scale_factor = usable_height / total_height;
            cell_width = ~~(cell_width * scale_factor);
            cell_height = ~~(cell_height * scale_factor);
        }
       return {
            width: cell_width,
            height: cell_height
        };
    }

    this.id_cell_size = function(cell_size) {
        var side = ~~(cell_size.height / this.id_cell_ratio);
        return {
            width: side,
            height: side
        }
    }

    this.top_left_corner = function(cell_size, canvas_width, canvas_height) {
        var tables_height = this.total_rows * cell_size.height;
        var extra_height;
        if (this.num_id_digits > 0) {
            extra_height = ~~(Defaults.id_bottom_line_dist * cell_size.height + cell_size.height / this.id_cell_ratio);
        } else {
            extra_height = 0;
        }
        return {
            x: ~~((canvas_width - cell_size.width * this.total_columns) / 2),
            y: ~~((canvas_height - tables_height - extra_height) / 2) + extra_height
        };
    }

    this.id_top_left_corner = function(cell_size, id_cell_size, top_left_corner, canvas_width) {
        return {
            x: ~~((canvas_width - id_cell_size.width * this.num_id_digits) / 2),
            y: top_left_corner.y - ~~(Defaults.id_bottom_line_dist * cell_size.height) - id_cell_size.height
        }
    }
}

var GeometryAnalyzer = {
    best_geometry: function(num_questions, num_choices, num_id_digits) {
        var geometries = [];
        for (var i = 1; i < 7; i++) {
            geometries.push(new Geometry(num_questions, num_choices, i, num_id_digits));
        }
        return this.choose_geometry(geometries);
    },

    choose_geometry: function(geometries) {
        var i;
        var best_dist = Infinity;
        var best_geometry;
        for (i in geometries) {
            var g = geometries[i];
            var dist = Math.abs(g.cell_ratio - Defaults.cell_ratio)
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