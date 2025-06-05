class Fraction {
  constructor(numerator, denominator = 1) {
    if (denominator === 0) {
      throw new Error("Denominator cannot be zero");
    }
    
    if (denominator < 0) {
      numerator = -numerator;
      denominator = -denominator;
    }
    
    const gcd = this.#gcd(Math.abs(numerator), Math.abs(denominator));
    this.numerator = numerator / gcd;
    this.denominator = denominator / gcd;
    
    Object.freeze(this);
  }
  
  #gcd(a, b) {
    while (b !== 0) {
      const temp = b;
      b = a % b;
      a = temp;
    }
    return a;
  }
  
  add(other) {
    if (!(other instanceof Fraction)) {
      throw new Error("Can only add another Fraction");
    }
    
    const newNumerator = this.numerator * other.denominator + other.numerator * this.denominator;
    const newDenominator = this.denominator * other.denominator;
    
    return new Fraction(newNumerator, newDenominator);
  }
  
  toMixedString() {
    const wholePart = Math.floor(Math.abs(this.numerator) / this.denominator);
    const remainder = Math.abs(this.numerator) % this.denominator;
    const isNegative = this.numerator < 0;
    
    if (wholePart === 0) {
      return this.toString();
    } else if (remainder === 0) {
      return (isNegative ? "-" : "") + wholePart.toString();
    } else {
      return (isNegative ? "-" : "") + wholePart + " " + remainder + "/" + this.denominator;
    }
  }
  
  toString() {
    if (this.denominator === 1) {
      return this.numerator.toString();
    }
    return this.numerator + "/" + this.denominator;
  }
  
  equals(other) {
    return other instanceof Fraction && 
           this.numerator === other.numerator && 
           this.denominator === other.denominator;
  }
  
  toDecimal() {
    return this.numerator / this.denominator;
  }
}

function parseFraction(str) {
  const parts = str.trim().split('/');
  if (parts.length === 1) {
    return new Fraction(parseInt(parts[0]));
  } else if (parts.length === 2) {
    return new Fraction(parseInt(parts[0]), parseInt(parts[1]));
  } else {
    throw new Error("Invalid fraction format");
  }
}

console.log("=== Fraction Addition Examples ===");

const frac1 = new Fraction(1, 2);
const frac2 = new Fraction(3, 4);
const result1 = frac1.add(frac2);
console.log(`${frac1.toString()} + ${frac2.toString()} = ${result1.toMixedString()}`);
console.log(`As improper fraction: ${result1.toString()}`);

const frac3 = new Fraction(1, 3);
const frac4 = new Fraction(1, 6);
const result2 = frac3.add(frac4);
console.log(`${frac3.toString()} + ${frac4.toString()} = ${result2.toString()}`);

const frac5 = new Fraction(2, 5);
const frac6 = new Fraction(1, 5);
const result3 = frac5.add(frac6);
console.log(`${frac5.toString()} + ${frac6.toString()} = ${result3.toString()}`);

const frac7 = new Fraction(6, 10);
console.log(`6/10 automatically reduces to: ${frac7.toString()}`);

const frac8 = new Fraction(-1, 2);
const frac9 = new Fraction(1, 4);
const result4 = frac8.add(frac9);
console.log(`${frac8.toString()} + ${frac9.toString()} = ${result4.toString()}`);

const frac10 = new Fraction(7, 3);
const frac11 = new Fraction(5, 6);
const result5 = frac10.add(frac11);
console.log(`${frac10.toMixedString()} + ${frac11.toString()} = ${result5.toMixedString()}`);

console.log("\n=== Testing Immutability ===");
const originalFrac = new Fraction(1, 2);
const addedFrac = originalFrac.add(new Fraction(1, 4));
console.log(`Original fraction unchanged: ${originalFrac.toString()}`);
console.log(`New fraction created: ${addedFrac.toString()}`);

try {
  originalFrac.numerator = 999;
} catch (e) {
  console.log("Cannot modify fraction - it's immutable");
}