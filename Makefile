.PHONY: help run test clean

help:
	@echo "Orderspector — make targets"
	@echo ""
	@echo "  make run     Run the reference implementation"
	@echo "  make test    Run the suite and verify expected numbers"
	@echo "  make clean   Remove build artifacts and caches"

run:
	cd code && python3 orderspector_reference.py

test:
	@cd code && python3 orderspector_reference.py > /tmp/orderspector_out.txt
	@grep -q "PART 1" /tmp/orderspector_out.txt && echo "PASS  Part 1: minimal instance"
	@grep -q "PART 2" /tmp/orderspector_out.txt && echo "PASS  Part 2: scaling law"
	@grep -q "88.6%" /tmp/orderspector_out.txt && echo "PASS  Part 2: L=12 saturation"
	@grep -q "PART 3" /tmp/orderspector_out.txt && echo "PASS  Part 3: corpus"
	@grep -q "15/16 = 94%" /tmp/orderspector_out.txt && echo "PASS  Part 3: precision"
	@grep -q "15/493 = 3%" /tmp/orderspector_out.txt && echo "PASS  Part 3: recall"
	@grep -q "PART 4" /tmp/orderspector_out.txt && echo "PASS  Part 4: LLVM bridge present"
	@grep -q "3/3 MATCH" /tmp/orderspector_out.txt && echo "PASS  Part 4: 3/3 matches"
	@echo ""
	@echo "All checks passed. Full output at /tmp/orderspector_out.txt"

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f /tmp/orderspector_out.txt
	rm -rf scratch/