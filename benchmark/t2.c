/*
 * file: t2.c
 * input: k in [200, 300]
 * output: k in [200, 300]
 */



int foo(int k) {
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

