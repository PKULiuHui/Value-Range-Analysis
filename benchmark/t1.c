/*
 * file: t1.c
 * input:
 * output: k in [100, 100]
 */


int foo() {
  int k = 0;
  while (k < 100) {
    int i = 0;
    int j = k;
    while (i < j) {
      i = i + 1;
      j = j - 1;
    }
    k = k + 1;
  }
  return k;
}

