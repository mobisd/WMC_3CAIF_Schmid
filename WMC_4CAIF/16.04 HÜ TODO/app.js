// 1. APPLICATION STATE
// - Holds the state of the application
// - This is the single source of truth for the application state

import TodoItem from "./todo-item.js";

const todos = [
  new TodoItem("WMC programmieren", false, 1),
  new TodoItem("CABS lernen", false, 3),
  new TodoItem("NSCS lernen", true, 2),
  new TodoItem("POS/Theorie lernen", false, 2),
  new TodoItem("POS/Java üben", false, 1),
];

// 2. STATE ACCESSORS/MUTATORS FN'S
// - Functions that allow us to get and set the state
// - Here we will create functions to add and remove todos

function addTodoItem(todo) {
  todos.push(todo);
}

function removeTodoItem(todo) {
  const idx = todos.indexOf(todo);
  if (idx !== -1) {
    todos.splice(idx, 1);
  }
}

function toggleTodoStatus(todo) {
  todo.toggleCompleted();
}

// 3. DOM Node Refs
// - Static references to DOM nodes needed after the start of the application

const newTodoText = document.getElementById("todo-input");
const newTodoPriority = document.getElementById("todo-priority");
const addBtn = document.getElementById("todo-add");
const filterText = document.getElementById("todo-filter-text");
const filterPriority = document.getElementById("todo-filter-priority");
const todoList = document.getElementById("todo-list");
const todoListDone = document.getElementById("todo-list-done");

// 4. DOM Node Creation Fn's
// - Dynamic creation of DOM nodes needed upon user interaction
// - Here we will create a function that will create a todo item

function getPriorityLabel(priority) {
  const labels = {
    1: "Sehr hoch",
    2: "Hoch",
    3: "Mittel",
    4: "Niedrig",
    5: "Sehr niedrig",
  };

  return labels[priority];
}

function createTodoElement(todo) {
  const listItem = document.createElement("li");
  listItem.className = "todo-item";
  listItem.dataset.priority = String(todo.priority);
  if (todo.completed) {
    listItem.classList.add("is-complete");
  }

  const cbDone = document.createElement("input");
  cbDone.type = "checkbox";
  cbDone.className = "todo-toggle";
  cbDone.checked = todo.completed;
  cbDone.addEventListener("change", (_) => onTodoStatusChanged(todo));

  const todoText = document.createElement("span");
  todoText.className = "todo-text";
  todoText.innerText = todo.text;

  const priorityBadge = document.createElement("span");
  priorityBadge.className = "todo-priority";
  priorityBadge.innerText = `Priorität ${todo.priority} - ${getPriorityLabel(todo.priority)}`;

  const content = document.createElement("div");
  content.className = "todo-content";
  content.append(todoText, priorityBadge);

  const priorityControls = document.createElement("div");
  priorityControls.className = "todo-priority-controls";

  const decreaseBtn = document.createElement("button");
  decreaseBtn.className = "todo-priority-btn";
  decreaseBtn.type = "button";
  decreaseBtn.innerText = "-";
  decreaseBtn.disabled = todo.priority === 5;
  decreaseBtn.setAttribute("aria-label", `Priorität von ${todo.text} senken`);
  decreaseBtn.addEventListener("click", (_) => onPriorityButtonClicked(todo, 1));

  const increaseBtn = document.createElement("button");
  increaseBtn.className = "todo-priority-btn";
  increaseBtn.type = "button";
  increaseBtn.innerText = "+";
  increaseBtn.disabled = todo.priority === 1;
  increaseBtn.setAttribute("aria-label", `Priorität von ${todo.text} erhöhen`);
  increaseBtn.addEventListener("click", (_) => onPriorityButtonClicked(todo, -1));

  priorityControls.append(decreaseBtn, increaseBtn);

  const deleteBtn = document.createElement("input");
  deleteBtn.className = "todo-delete";
  deleteBtn.value = "Delete";
  deleteBtn.type = "button";
  deleteBtn.addEventListener("click", (_) => onDeleteButtonClicked(todo));

  listItem.append(cbDone, content, priorityControls, deleteBtn);
  return listItem;
}

// 5. RENDER FN
// - These functions will render the application state to the DOM
// - Here we will use a very naive but simple approach to re-render the list
// - IMPORTANT TAKEAWAY: The state drives the UI, any state change should trigger a re-render of the UI

function render() {
  todoList.innerHTML = "";
  todoListDone.innerHTML = "";
  const searchTerm = filterText.value.trim().toLowerCase();
  const selectedPriority = filterPriority.value;
  const sortedTodos = [...todos].sort((a, b) => {
    if (a.completed !== b.completed) {
      return Number(a.completed) - Number(b.completed);
    }

    return a.priority - b.priority;
  });

  for (const ti of sortedTodos) {
    const matchesText = ti.text.toLowerCase().includes(searchTerm);
    const matchesPriority =
      selectedPriority === "all" || ti.priority === Number(selectedPriority);

    if (!matchesText || !matchesPriority) {
      continue;
    }

    const todoElement = createTodoElement(ti);
    if (!ti.completed) {
      todoList.append(todoElement);
    } else {
      todoListDone.append(todoElement);
    }
  }
}

// 6. EVENT HANDLERS
// - These functions handle user interaction e.g. button clicks, key presses etc.
// - These functions will call the state mutators and then call the render function
// - The naming convention for the event handlers is `on<Event>`
// - Here we will create a function that will handle the add button click

function onAddButtonClicked() {
  if (newTodoText.value.trim() !== "") {
    const priority = Number(newTodoPriority.value);
    const ti = new TodoItem(newTodoText.value.trim(), false, priority);
    addTodoItem(ti);
    newTodoText.value = "";
    newTodoPriority.value = "3";
    render();
  }
}

function onDeleteButtonClicked(todo) {
  removeTodoItem(todo);
  render();
}

function onTodoStatusChanged(todo) {
  toggleTodoStatus(todo);
  render();
}

function onPriorityButtonClicked(todo, change) {
  const nextPriority = Math.min(5, Math.max(1, todo.priority + change));
  todo.priority = nextPriority;
  render();
}

function onKeyDownEvent(e) {
  if (e.key === "Enter") {
    onAddButtonClicked();
  }
}

// 7. INIT BINDINGS
// - These are the initial bindings of the event handlers

addBtn.addEventListener("click", (_) => onAddButtonClicked());
newTodoText.addEventListener("keydown", (e) => onKeyDownEvent(e));
filterText.addEventListener("input", () => render());
filterPriority.addEventListener("change", () => render());
// 8. INITIAL RENDER
// - Here will call the render function to render the initial state of the application

render();
