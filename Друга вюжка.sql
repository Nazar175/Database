WITH OrderProducts AS (
    SELECT 
        od.OrderID,
        SUM(od.Quantity * p.Price) AS ProductsTotal
    FROM OrderDetail od
    JOIN Product p ON od.ProductID = p.ProductID
    GROUP BY od.OrderID
),
OrderCourier AS (
    SELECT 
        c.OrderID,
        c.Price AS CourierPrice
    FROM Courier c
),
OrderGifts AS (
    SELECT 
        o.OrderID,
        SUM(
            CASE 
                WHEN g.Unit = 'USD' THEN g.Amount
                WHEN g.Unit = '%' THEN g.Amount / 100 * op.ProductsTotal
                ELSE 0
            END
        ) AS GiftAmount
    FROM Orders o
    LEFT JOIN Payment p ON o.OrderID = p.OrderID
    LEFT JOIN Gifts g ON p.PaymentID = g.PaymentID
    LEFT JOIN (
        SELECT 
            od.OrderID,
            SUM(od.Quantity * pr.Price) AS ProductsTotal
        FROM OrderDetail od
        JOIN Product pr ON od.ProductID = pr.ProductID
        GROUP BY od.OrderID
    ) op ON o.OrderID = op.OrderID
    GROUP BY o.OrderID
)
SELECT 
    o.OrderID,
    COALESCE(op.ProductsTotal,0) + COALESCE(c.CourierPrice,0) - COALESCE(g.GiftAmount,0) AS TotalToPay,
    COALESCE(op.ProductsTotal,0) AS ProductsTotal,
    COALESCE(c.CourierPrice,0) AS CourierPrice,
    COALESCE(g.GiftAmount,0) AS GiftAmount
FROM Orders o
LEFT JOIN OrderProducts op ON o.OrderID = op.OrderID
LEFT JOIN OrderCourier c ON o.OrderID = c.OrderID
LEFT JOIN OrderGifts g ON o.OrderID = g.OrderID
ORDER BY o.OrderID;