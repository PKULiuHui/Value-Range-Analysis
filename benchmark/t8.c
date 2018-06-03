/*
 * file: t1.c
 * input: a in [1, 100] 
 *        b in [-2, 2]
 * output: ret in [-3.2192308, 5.94230769]
 */


float foo(int a, int b) {
   float i, j, k;
   if(a){
       i = 10.3;
       j = 5.2;
       k = i / j;
   } else {
       i = 7.3;
       j = 2.4;
       k = i - j;
   }

   float ret = 0;

   if(b) {
	ret = k - j;
   } else {
	ret = k * 3.0;
   }

   return ret;
}

