document.addEventListener("DOMContentLoaded", function () {

    function renumberDirections(container) {
        var numbers = container.querySelectorAll(".direction-number");
        for (var i = 0; i < numbers.length; i++) {
            numbers[i].textContent = i + 1;
        }
    }

    // Event delegation for remove, move up, move down
    document.addEventListener("click", function (e) {
        var removeBtn = e.target.closest(".btn-remove");
        if (removeBtn) {
            var row = removeBtn.closest(".ingredient-row, .direction-row, .item-row");
            if (row) {
                var container = row.parentElement;
                // Keep at least one row
                if (container.children.length > 1) {
                    row.remove();
                    renumberDirections(container);
                }
            }
            return;
        }

        var upBtn = e.target.closest(".btn-up");
        if (upBtn) {
            var row = upBtn.closest(".direction-row");
            if (row && row.previousElementSibling) {
                row.parentElement.insertBefore(row, row.previousElementSibling);
                renumberDirections(row.parentElement);
            }
            return;
        }

        var downBtn = e.target.closest(".btn-down");
        if (downBtn) {
            var row = downBtn.closest(".direction-row");
            if (row && row.nextElementSibling) {
                row.parentElement.insertBefore(row.nextElementSibling, row);
                renumberDirections(row.parentElement);
            }
            return;
        }
    });

    function addRow(containerId) {
        var container = document.getElementById(containerId);
        if (!container) return;
        var firstRow = container.children[0];
        if (!firstRow) return;
        var clone = firstRow.cloneNode(true);
        var inputs = clone.querySelectorAll("input, textarea");
        for (var i = 0; i < inputs.length; i++) {
            inputs[i].value = "";
        }
        container.appendChild(clone);
        renumberDirections(container);
        // Focus the first input in the new row
        var first = clone.querySelector("input");
        if (first) first.focus();
    }

    var addIngBtn = document.getElementById("add-ingredient");
    if (addIngBtn) {
        addIngBtn.addEventListener("click", function () {
            addRow("ingredients-container");
        });
    }

    var addDirBtn = document.getElementById("add-direction");
    if (addDirBtn) {
        addDirBtn.addEventListener("click", function () {
            addRow("directions-container");
        });
    }

    var addItemBtn = document.getElementById("add-item");
    if (addItemBtn) {
        addItemBtn.addEventListener("click", function () {
            addRow("items-container");
        });
    }

});
