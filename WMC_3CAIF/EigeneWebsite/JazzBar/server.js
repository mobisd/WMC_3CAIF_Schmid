const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const bodyParser = require("body-parser");
const cors = require("cors");
const path = require("path");

const app = express();
const port = 3000;

app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, ".")));

// dartenbarnk
const db = new sqlite3.Database("lighthouse.db", (err) => {
  if (err) {
    console.error("Error opening database", err.message);
  } else {
    console.log("Connected to the SQLite database.");
    db.run(
      `CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            guests INTEGER NOT NULL,
            request TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )`,
      (err) => {
        if (err) {
          console.error("Error creating table", err.message);
        }
      }
    );
  }
});

// seats
const TOTAL_SEATS = 40;

// shit das alles geht

// übrige sitzplötze getten
app.get("/api/availability", (req, res) => {
  const { date } = req.query;

  if (!date) {
    return res.status(400).json({ error: "Date is required" });
  }

  // gäste zählen für den ganzen tag lmao
  const sql = `SELECT SUM(guests) as booked_seats FROM bookings WHERE date = ?`;

  db.get(sql, [date], (err, row) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    const booked = row.booked_seats || 0;
    const seatsLeft = Math.max(0, TOTAL_SEATS - booked);
    res.json({ seatsLeft, booked });
  });
});

// neue reservierte vierung
app.post("/api/book", (req, res) => {
  const { name, email, date, time, guests, request } = req.body;

  if (!name || !date || !time || !guests) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const guestCount = parseInt(guests, 10);

  // mussi kucki ob platz wenn nicht dann schadi
  const sqlCheck = `SELECT SUM(guests) as booked_seats FROM bookings WHERE date = ?`;

  db.get(sqlCheck, [date], (err, row) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    const booked = row.booked_seats || 0;
    if (booked + guestCount > TOTAL_SEATS) {
      return res
        .status(400)
        .json({ error: "Not enough seats available for this date" });
    }

    // reservierung in datenbank rein (IN DICH REIN)
    const sqlInsert = `INSERT INTO bookings (name, email, date, time, guests, request) VALUES (?, ?, ?, ?, ?, ?)`;
    db.run(
      sqlInsert,
      [name, email, date, time, guestCount, request],
      function (err) {
        if (err) {
          return res.status(500).json({ error: err.message });
        }
        res.json({
          message: "Booking confirmed",
          bookingId: this.lastID,
          seatsLeft: TOTAL_SEATS - (booked + guestCount),
        });
      }
    );
  });
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}/`);
});
