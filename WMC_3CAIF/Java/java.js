const numberCount = 5; 
const min = -2;
const max = 102;

const range = max - min;
const array = [];

for (let i = 0; i < numberCount; i++) {
     array.push(Math.round(Math.random() * range + min));
}
console.log("Vorher:", array); // Nur zum Testen

array.sort((a, b) => a - b);

console.log("Nachher:", array);