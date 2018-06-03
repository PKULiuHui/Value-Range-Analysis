/*
 * file: t4.c
 * input: argc in [-inf, +inf]
 * output: k in [0, +inf]
 */


int foo(int argc) {
  int k = 0;
  while (k < argc) {
    k = k + 1;
  }
  return k;
}

