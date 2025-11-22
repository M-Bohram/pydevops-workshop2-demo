document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("todo-form");
  const todosList = document.getElementById("todos-list");
  const messageDiv = document.getElementById("message");

  function showMessage(text, isError = false) {
    messageDiv.textContent = text;
    messageDiv.className = isError ? "message error" : "message success";
    if (text) {
      setTimeout(() => {
        messageDiv.textContent = "";
        messageDiv.className = "message";
      }, 3000);
    }
  }

  async function fetchTodos() {
    try {
      const res = await fetch("/api/todos");
      if (!res.ok) {
        throw new Error("Failed to fetch todos");
      }
      const todos = await res.json();
      renderTodos(todos);
    } catch (err) {
      console.error(err);
      showMessage("Error loading todos", true);
    }
  }

  function renderTodos(todos) {
    todosList.innerHTML = "";
    if (todos.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No todos yet. Add one above!";
      li.classList.add("empty");
      todosList.appendChild(li);
      return;
    }

    todos.forEach((todo) => {
      const li = document.createElement("li");
      li.classList.add("todo-item");

      const header = document.createElement("div");
      header.classList.add("todo-header");

      const title = document.createElement("span");
      title.classList.add("todo-title");
      title.textContent = todo.title;

      const date = document.createElement("span");
      date.classList.add("todo-date");
      const createdAt = new Date(todo.created_at);
      date.textContent = createdAt.toLocaleString();

      header.appendChild(title);
      header.appendChild(date);

      const body = document.createElement("div");
      body.classList.add("todo-body");
      if (todo.description) {
        const desc = document.createElement("p");
        desc.textContent = todo.description;
        body.appendChild(desc);
      } else {
        const noDesc = document.createElement("p");
        noDesc.textContent = "(No description)";
        noDesc.classList.add("muted");
        body.appendChild(noDesc);
      }

      if (todo.file_url) {
        const fileLink = document.createElement("a");
        fileLink.href = todo.file_url;
        fileLink.target = "_blank";
        fileLink.textContent = "Attached file";
        fileLink.classList.add("file-link");
        body.appendChild(fileLink);
      }

      li.appendChild(header);
      li.appendChild(body);
      todosList.appendChild(li);
    });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(form);

    try {
      const res = await fetch("/api/todos", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const errMsg = data.error || "Failed to create todo";
        throw new Error(errMsg);
      }

      showMessage("Todo created successfully");
      form.reset();
      await fetchTodos();
    } catch (err) {
      console.error(err);
      showMessage(err.message || "Error creating todo", true);
    }
  });

  // Initial load
  fetchTodos();
});
