import persons from "./persons.json" with { type: "json" };

const sortState = {
    key: "id",
    direction: "asc",
};

function renderPersons() {
    const tbody = document.querySelector("#tbody");
    tbody.innerHTML = "";
    for (const person of persons) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${person.id}</td>
            <td>${person.name}</td>
            <td>${person.groesse}</td>
            <td>${person.geburtsdatum}</td>
            <td>${person.herkunft}</td>
            <td>${person.gewicht}</td>
        `;
        tbody.appendChild(tr);
    }
}

function comparePersons(a, b, key, type) {
    if (type === "number") {
        return a[key] - b[key];
    }

    if (type === "date") {
        return new Date(a[key]) - new Date(b[key]);
    }

    return a[key].localeCompare(b[key]);
}

function sortPersons(key, type) {
    if (sortState.key === key) {
        sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
    } else {
        sortState.key = key;
        sortState.direction = "asc";
    }

    persons.sort((a, b) => {
        const result = comparePersons(a, b, key, type);
        return sortState.direction === "asc" ? result : -result;
    });

    renderPersons();
    updateTableHeaders();
}

function updateTableHeaders() {
    const tableHeaders = document.querySelectorAll("th[data-sort]");

    for (const tableHeader of tableHeaders) {
        const label = tableHeader.dataset.label ?? tableHeader.textContent;
        tableHeader.dataset.label = label.replace(" [asc]", "").replace(" [desc]", "");
        tableHeader.textContent = tableHeader.dataset.label;

        if (tableHeader.dataset.sort === sortState.key) {
            tableHeader.textContent += sortState.direction === "asc" ? " [asc]" : " [desc]";
        }
    }
}

const tableHeaders = document.querySelectorAll("th[data-sort]");

for (const tableHeader of tableHeaders) {
    tableHeader.addEventListener("click", () => {
        sortPersons(tableHeader.dataset.sort, tableHeader.dataset.type);
    });
}

renderPersons();
updateTableHeaders();
