const students = [
  { name: "Anna", age: 17, grade: 2 },
  { name: "Ben", age: 16, grade: 4 },
  { name: "Clara", age: 18, grade: 1 },
  { name: "David", age: 17, grade: 5 },
  { name: "Elena", age: 16, grade: 3 },
  { name: "Felix", age: 19, grade: 2 },
  { name: "Gina", age: 17, grade: 1 },
  { name: "Hugo", age: 18, grade: 4 },
];

// Task 1
const passed = students.filter(s => s.grade <= 4);

// Task 2
const labels = students.map(s => `${s.name} (${s.age})`);

// Task 3
const passedNames = students
  .filter(s => s.grade <= 4)
  .map(s => s.name);

// Task 4
const averageGrade = students.reduce((acc, s) => acc + s.grade, 0) / students.length;

// Task 5
const result = students
  .filter(s => s.age >= 17)
  .filter(s => s.grade <= 4)
  .map(s => s.name)
  .join(", ");

console.log("passed:", passed);
console.log("labels:", labels);
console.log("passedNames:", passedNames);
console.log("averageGrade:", averageGrade);
console.log("result:", result);